package com.videomanager.repository;

import com.videomanager.api.ApiClient;
import com.videomanager.model.Video;
import java.util.List;
import retrofit2.Call;
import retrofit2.Response;

public class ServerRepository implements VideoRepository {

    @Override
    public void listVideos(Callback<List<Video>> callback) {
        ApiClient.getService().listVideos().enqueue(new retrofit2.Callback<List<Video>>() {
            @Override
            public void onResponse(Call<List<Video>> call, Response<List<Video>> response) {
                if (response.isSuccessful() && response.body() != null) {
                    callback.onSuccess(response.body());
                } else {
                    callback.onError("Server error " + response.code());
                }
            }

            @Override
            public void onFailure(Call<List<Video>> call, Throwable t) {
                callback.onError(t.getMessage());
            }
        });
    }

    @Override
    public void deleteVideo(String filename, Callback<Void> callback) {
        ApiClient.getService().deleteVideo(filename).enqueue(new retrofit2.Callback<Void>() {
            @Override
            public void onResponse(Call<Void> call, Response<Void> response) {
                if (response.isSuccessful()) {
                    callback.onSuccess(null);
                } else {
                    callback.onError("Delete failed " + response.code());
                }
            }

            @Override
            public void onFailure(Call<Void> call, Throwable t) {
                callback.onError(t.getMessage());
            }
        });
    }
}
