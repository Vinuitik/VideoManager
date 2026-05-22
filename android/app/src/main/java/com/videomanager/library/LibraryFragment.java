package com.videomanager.library;

import android.os.Bundle;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.fragment.app.Fragment;
import androidx.media3.common.MediaItem;
import androidx.media3.exoplayer.ExoPlayer;
import com.google.android.material.snackbar.Snackbar;
import com.videomanager.BuildConfig;
import com.videomanager.databinding.FragmentLibraryBinding;
import com.videomanager.model.Video;
import com.videomanager.repository.ServerRepository;
import com.videomanager.repository.VideoRepository;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.List;

public class LibraryFragment extends Fragment {

    private FragmentLibraryBinding binding;
    private VideoAdapter adapter;
    private VideoRepository repository;
    private ExoPlayer player;

    @Override
    public View onCreateView(@NonNull LayoutInflater inflater, ViewGroup container, Bundle savedInstanceState) {
        binding = FragmentLibraryBinding.inflate(inflater, container, false);
        return binding.getRoot();
    }

    @Override
    public void onViewCreated(@NonNull View view, @Nullable Bundle savedInstanceState) {
        super.onViewCreated(view, savedInstanceState);

        repository = new ServerRepository();

        player = new ExoPlayer.Builder(requireContext()).build();
        binding.playerView.setPlayer(player);

        adapter = new VideoAdapter(this::playVideo, this::deleteVideo);
        binding.recyclerView.setAdapter(adapter);

        binding.closePlayer.setOnClickListener(v -> hidePlayer());

        loadVideos();
    }

    private void loadVideos() {
        if (binding == null) return;
        binding.progressBar.setVisibility(View.VISIBLE);

        repository.listVideos(new VideoRepository.Callback<List<Video>>() {
            @Override
            public void onSuccess(List<Video> videos) {
                if (binding == null) return;
                binding.progressBar.setVisibility(View.GONE);
                adapter.setVideos(videos);
                binding.emptyText.setVisibility(videos.isEmpty() ? View.VISIBLE : View.GONE);
            }

            @Override
            public void onError(String message) {
                if (binding == null) return;
                binding.progressBar.setVisibility(View.GONE);
                Snackbar.make(binding.getRoot(), "Failed to load: " + message, Snackbar.LENGTH_LONG).show();
            }
        });
    }

    private void playVideo(Video video) {
        String encoded = URLEncoder.encode(video.name, StandardCharsets.UTF_8).replace("+", "%20");
        String url = BuildConfig.SERVER_URL + "/videos/" + encoded;
        player.setMediaItem(MediaItem.fromUri(url));
        player.prepare();
        player.play();
        binding.playerView.setVisibility(View.VISIBLE);
        binding.closePlayer.setVisibility(View.VISIBLE);
    }

    private void deleteVideo(Video video) {
        repository.deleteVideo(video.name, new VideoRepository.Callback<Void>() {
            @Override
            public void onSuccess(Void result) {
                if (binding == null) return;
                adapter.removeVideo(video);
            }

            @Override
            public void onError(String message) {
                if (binding == null) return;
                Snackbar.make(binding.getRoot(), "Delete failed: " + message, Snackbar.LENGTH_LONG).show();
            }
        });
    }

    private void hidePlayer() {
        player.stop();
        binding.playerView.setVisibility(View.GONE);
        binding.closePlayer.setVisibility(View.GONE);
    }

    @Override
    public void onDestroyView() {
        super.onDestroyView();
        player.release();
        player = null;
        binding = null;
    }
}
