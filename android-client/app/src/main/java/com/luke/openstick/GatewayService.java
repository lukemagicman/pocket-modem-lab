package com.luke.openstick;

import android.app.Service;
import android.content.Intent;
import android.database.Cursor;
import android.net.Uri;
import android.os.IBinder;
import android.telephony.ServiceState;
import android.telephony.PhoneStateListener;
import android.telephony.TelephonyManager;
import android.util.Log;

import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.InputStreamReader;
import java.io.OutputStreamWriter;
import java.net.InetAddress;
import java.net.ServerSocket;
import java.net.Socket;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class GatewayService extends Service {
    private static final String TAG = "OpenStickGateway";
    private static final int PORT = 18081;
    private volatile boolean running;
    private ServerSocket serverSocket;
    private ExecutorService workers;
    private TelephonyManager telephonyManager;
    private volatile ServiceState lastServiceState;
    private final PhoneStateListener phoneStateListener = new PhoneStateListener() {
        @Override
        public void onServiceStateChanged(ServiceState serviceState) {
            lastServiceState = serviceState;
        }
    };

    @Override
    public void onCreate() {
        super.onCreate();
        workers = Executors.newFixedThreadPool(3);
        telephonyManager = (TelephonyManager) getSystemService(TELEPHONY_SERVICE);
        if (telephonyManager != null) {
            telephonyManager.listen(phoneStateListener, PhoneStateListener.LISTEN_SERVICE_STATE);
        }
        startServer();
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        return START_STICKY;
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    @Override
    public void onDestroy() {
        running = false;
        try {
            if (serverSocket != null) {
                serverSocket.close();
            }
        } catch (Exception ignored) {
        }
        if (workers != null) {
            workers.shutdownNow();
        }
        if (telephonyManager != null) {
            telephonyManager.listen(phoneStateListener, PhoneStateListener.LISTEN_NONE);
        }
        super.onDestroy();
    }

    private void startServer() {
        new Thread(new Runnable() {
            @Override
            public void run() {
                try {
                    serverSocket = new ServerSocket(PORT, 8, InetAddress.getByName("127.0.0.1"));
                    running = true;
                    Log.i(TAG, "Read-only gateway listening on loopback:" + PORT);
                    while (running) {
                        final Socket socket = serverSocket.accept();
                        workers.execute(new Runnable() {
                            @Override
                            public void run() {
                                handle(socket);
                            }
                        });
                    }
                } catch (Exception error) {
                    if (running) {
                        Log.e(TAG, "Gateway stopped", error);
                    }
                }
            }
        }, "openstick-http").start();
    }

    private void handle(Socket socket) {
        try {
            socket.setSoTimeout(5000);
            BufferedReader reader = new BufferedReader(new InputStreamReader(socket.getInputStream(), "UTF-8"));
            String requestLine = reader.readLine();
            String line;
            while ((line = reader.readLine()) != null && line.length() > 0) {
                // Headers are intentionally ignored in the loopback-only prototype.
            }

            if (requestLine == null || !requestLine.startsWith("GET ")) {
                respond(socket, 405, "application/json", "{\"error\":\"read_only_get_required\"}");
                return;
            }

            String target = requestLine.split(" ")[1];
            if (target.equals("/api/health")) {
                respond(socket, 200, "application/json", "{\"ok\":true,\"mode\":\"readonly\"}");
            } else if (target.equals("/api/status")) {
                respond(socket, 200, "application/json", statusJson());
            } else if (target.startsWith("/api/messages")) {
                respond(socket, 200, "application/json", messagesJson(parseLimit(target)));
            } else if (target.equals("/") || target.startsWith("/index.html")) {
                respond(socket, 200, "text/html; charset=utf-8", pageHtml());
            } else {
                respond(socket, 404, "application/json", "{\"error\":\"not_found\"}");
            }
        } catch (SecurityException denied) {
            try {
                respond(socket, 403, "application/json", "{\"error\":\"permission_denied\"}");
            } catch (Exception ignored) {
            }
        } catch (Exception error) {
            Log.e(TAG, "Request failed", error);
        } finally {
            try {
                socket.close();
            } catch (Exception ignored) {
            }
        }
    }

    private String statusJson() {
        TelephonyManager telephony = telephonyManager;
        String operator = telephony == null ? "" : telephony.getNetworkOperatorName();
        String simOperator = telephony == null ? "" : telephony.getSimOperator();
        int simState = telephony == null ? TelephonyManager.SIM_STATE_UNKNOWN : telephony.getSimState();
        int networkType = telephony == null ? TelephonyManager.NETWORK_TYPE_UNKNOWN : telephony.getNetworkType();
        ServiceState serviceState = lastServiceState;
        int voiceState = serviceState == null ? -1 : serviceState.getState();

        return "{"
                + "\"simState\":" + simState + ","
                + "\"simOperator\":\"" + json(simOperator) + "\","
                + "\"operator\":\"" + json(operator) + "\","
                + "\"networkType\":" + networkType + ","
                + "\"serviceState\":" + voiceState + ","
                + "\"mode\":\"readonly\""
                + "}";
    }

    private String messagesJson(int limit) {
        Cursor cursor = null;
        StringBuilder out = new StringBuilder("{\"messages\":[");
        int count = 0;
        try {
            cursor = getContentResolver().query(
                    Uri.parse("content://sms"),
                    new String[]{"_id", "thread_id", "address", "body", "date", "type", "read", "status"},
                    null,
                    null,
                    "date DESC"
            );
            if (cursor != null) {
                while (cursor.moveToNext() && count < limit) {
                    if (count > 0) {
                        out.append(',');
                    }
                    out.append('{')
                            .append("\"id\":").append(cursor.getLong(0)).append(',')
                            .append("\"threadId\":").append(cursor.getLong(1)).append(',')
                            .append("\"address\":\"").append(json(cursor.getString(2))).append("\",")
                            .append("\"body\":\"").append(json(cursor.getString(3))).append("\",")
                            .append("\"date\":").append(cursor.getLong(4)).append(',')
                            .append("\"type\":").append(cursor.getInt(5)).append(',')
                            .append("\"read\":").append(cursor.getInt(6)).append(',')
                            .append("\"status\":").append(cursor.getInt(7))
                            .append('}');
                    count++;
                }
            }
        } finally {
            if (cursor != null) {
                cursor.close();
            }
        }
        out.append("],\"count\":").append(count).append(",\"mode\":\"readonly\"}");
        return out.toString();
    }

    private int parseLimit(String target) {
        int fallback = 50;
        int marker = target.indexOf("limit=");
        if (marker < 0) {
            return fallback;
        }
        try {
            String raw = target.substring(marker + 6).split("&")[0];
            int value = Integer.parseInt(raw);
            return Math.max(1, Math.min(value, 200));
        } catch (Exception ignored) {
            return fallback;
        }
    }

    private void respond(Socket socket, int code, String contentType, String body) throws Exception {
        byte[] bytes = body.getBytes("UTF-8");
        BufferedWriter writer = new BufferedWriter(new OutputStreamWriter(socket.getOutputStream(), "UTF-8"));
        writer.write("HTTP/1.1 " + code + " " + reason(code) + "\r\n");
        writer.write("Content-Type: " + contentType + "\r\n");
        writer.write("Content-Length: " + bytes.length + "\r\n");
        writer.write("Cache-Control: no-store\r\n");
        writer.write("Connection: close\r\n\r\n");
        writer.flush();
        socket.getOutputStream().write(bytes);
        socket.getOutputStream().flush();
    }

    private String reason(int code) {
        if (code == 200) return "OK";
        if (code == 403) return "Forbidden";
        if (code == 404) return "Not Found";
        return "Method Not Allowed";
    }

    private String pageHtml() {
        return "<!doctype html><html lang=zh-CN><meta charset=utf-8>"
                + "<meta name=viewport content=width=device-width,initial-scale=1>"
                + "<title>Pocket Modem Lab</title><style>"
                + "body{font:16px sans-serif;margin:28px;background:#f4f6f8;color:#17202a}"
                + ".card{max-width:720px;margin:auto;background:white;padding:24px;border-radius:16px;box-shadow:0 8px 30px #0001}"
                + "pre{white-space:pre-wrap;background:#f7f8fa;padding:16px;border-radius:10px}"
                + "</style><div class=card><h2>Pocket Modem Lab Android 客户端</h2>"
                + "<p>只读实验版：不发送短信，不修改网络。</p><pre id=out>正在读取…</pre></div>"
                + "<script>var x=new XMLHttpRequest();x.onreadystatechange=function(){"
                + "if(x.readyState===4){document.getElementById('out').textContent=x.status===200?"
                + "JSON.stringify(JSON.parse(x.responseText),null,2):'读取失败：'+x.status}};"
                + "x.open('GET','/api/status',true);x.send();</script></html>";
    }

    private String json(String value) {
        if (value == null) {
            return "";
        }
        return value.replace("\\", "\\\\")
                .replace("\"", "\\\"")
                .replace("\r", "\\r")
                .replace("\n", "\\n")
                .replace("\t", "\\t");
    }
}
