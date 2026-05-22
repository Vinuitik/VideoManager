package com.videomanager.api;

import com.videomanager.model.DownloadRequest;
import com.videomanager.model.DownloadResponse;
import com.videomanager.model.Video;
import java.util.List;
import retrofit2.Call;
import retrofit2.http.Body;
import retrofit2.http.DELETE;
import retrofit2.http.GET;
import retrofit2.http.POST;
import retrofit2.http.Path;

public interface VideoApiService {

    @GET("api/videos/")
    Call<List<Video>> listVideos();

    @DELETE("api/videos/{filename}")
    Call<Void> deleteVideo(@Path("filename") String filename);

    @POST("api/v1/download")
    Call<DownloadResponse> startDownload(@Body DownloadRequest request);
}
