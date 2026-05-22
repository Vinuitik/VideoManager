package com.videomanager.download;

import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.fragment.app.Fragment;
import com.google.gson.Gson;
import com.google.gson.JsonObject;
import com.videomanager.BuildConfig;
import com.videomanager.api.ApiClient;
import com.videomanager.databinding.FragmentDownloadBinding;
import okhttp3.Request;
import okhttp3.WebSocket;
import okhttp3.WebSocketListener;

public class DownloadFragment extends Fragment {

    private FragmentDownloadBinding binding;
    private WebSocket activeSocket;
    private final Handler mainHandler = new Handler(Looper.getMainLooper());
    private final Gson gson = new Gson();

    @Override
    public View onCreateView(@NonNull LayoutInflater inflater, ViewGroup container, Bundle savedInstanceState) {
        binding = FragmentDownloadBinding.inflate(inflater, container, false);
        return binding.getRoot();
    }

    @Override
    public void onViewCreated(@NonNull View view, @Nullable Bundle savedInstanceState) {
        super.onViewCreated(view, savedInstanceState);
        binding.downloadButton.setOnClickListener(v -> startDownload());
    }

    private void startDownload() {
        String url = binding.urlInput.getText().toString().trim();
        if (url.isEmpty()) return;

        setUiDownloading(true);
        binding.statusText.setText("Connecting…");

        if (activeSocket != null) {
            activeSocket.cancel();
        }

        String wsUrl = BuildConfig.SERVER_URL
                .replace("https://", "wss://")
                .replace("http://", "ws://")
                + "/api/v2/download";

        Request request = new Request.Builder().url(wsUrl).build();
        activeSocket = ApiClient.getOkHttpClient().newWebSocket(request, new WebSocketListener() {

            @Override
            public void onOpen(@NonNull WebSocket ws, @NonNull okhttp3.Response response) {
                JsonObject payload = new JsonObject();
                payload.addProperty("url", url);
                ws.send(gson.toJson(payload));
            }

            @Override
            public void onMessage(@NonNull WebSocket ws, @NonNull String text) {
                JsonObject msg = gson.fromJson(text, JsonObject.class);
                String type = msg.has("type") ? msg.get("type").getAsString() : "";
                mainHandler.post(() -> {
                    if (binding == null) return;
                    switch (type) {
                        case "progress":
                            int pct = msg.has("progress") ? (int) msg.get("progress").getAsDouble() : 0;
                            String speed = msg.has("speed") ? msg.get("speed").getAsString() : "";
                            String eta = msg.has("eta") ? msg.get("eta").getAsString() : "";
                            binding.progressBar.setProgress(pct);
                            binding.statusText.setText(pct + "% — " + speed + " — ETA " + eta);
                            break;
                        case "done":
                            binding.progressBar.setProgress(100);
                            binding.statusText.setText("Done");
                            setUiDownloading(false);
                            binding.urlInput.setText("");
                            break;
                        case "error":
                            String err = msg.has("message") ? msg.get("message").getAsString() : "Unknown error";
                            binding.statusText.setText("Error: " + err);
                            setUiDownloading(false);
                            break;
                    }
                });
            }

            @Override
            public void onFailure(@NonNull WebSocket ws, @NonNull Throwable t, @Nullable okhttp3.Response response) {
                mainHandler.post(() -> {
                    if (binding == null) return;
                    binding.statusText.setText("Connection failed: " + t.getMessage());
                    setUiDownloading(false);
                });
            }

            @Override
            public void onClosed(@NonNull WebSocket ws, int code, @NonNull String reason) {
                mainHandler.post(() -> {
                    if (binding == null) return;
                    // Guard: if progress message set "Done" already, don't overwrite
                    if (!binding.statusText.getText().toString().equals("Done")) {
                        binding.statusText.setText("Done");
                    }
                    setUiDownloading(false);
                });
            }
        });
    }

    private void setUiDownloading(boolean downloading) {
        if (binding == null) return;
        binding.downloadButton.setEnabled(!downloading);
        binding.urlInput.setEnabled(!downloading);
        if (!downloading) binding.progressBar.setProgress(0);
    }

    @Override
    public void onDestroyView() {
        super.onDestroyView();
        if (activeSocket != null) {
            activeSocket.cancel();
            activeSocket = null;
        }
        binding = null;
    }
}
