package com.videomanager.repository;

import com.videomanager.model.Video;
import java.util.List;

public interface VideoRepository {

    interface Callback<T> {
        void onSuccess(T result);
        void onError(String message);
    }

    void listVideos(Callback<List<Video>> callback);
    void deleteVideo(String filename, Callback<Void> callback);
}
