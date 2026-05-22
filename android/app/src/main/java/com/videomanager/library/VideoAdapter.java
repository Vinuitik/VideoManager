package com.videomanager.library;

import android.view.LayoutInflater;
import android.view.ViewGroup;
import androidx.annotation.NonNull;
import androidx.recyclerview.widget.RecyclerView;
import com.videomanager.databinding.ItemVideoBinding;
import com.videomanager.model.Video;
import java.util.ArrayList;
import java.util.List;

public class VideoAdapter extends RecyclerView.Adapter<VideoAdapter.ViewHolder> {

    interface OnPlayClick { void play(Video video); }
    interface OnDeleteClick { void delete(Video video); }

    private List<Video> videos = new ArrayList<>();
    private final OnPlayClick onPlay;
    private final OnDeleteClick onDelete;

    VideoAdapter(OnPlayClick onPlay, OnDeleteClick onDelete) {
        this.onPlay = onPlay;
        this.onDelete = onDelete;
    }

    void setVideos(List<Video> list) {
        videos = new ArrayList<>(list);
        notifyDataSetChanged();
    }

    void removeVideo(Video video) {
        int pos = videos.indexOf(video);
        if (pos >= 0) {
            videos.remove(pos);
            notifyItemRemoved(pos);
        }
    }

    @NonNull
    @Override
    public ViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
        ItemVideoBinding b = ItemVideoBinding.inflate(
                LayoutInflater.from(parent.getContext()), parent, false);
        return new ViewHolder(b);
    }

    @Override
    public void onBindViewHolder(@NonNull ViewHolder h, int pos) {
        Video v = videos.get(pos);
        h.binding.videoName.setText(v.name);
        h.binding.videoSize.setText(formatSize(v.size));
        h.binding.playButton.setOnClickListener(view -> onPlay.play(v));
        h.binding.deleteButton.setOnClickListener(view -> onDelete.delete(v));
    }

    @Override
    public int getItemCount() { return videos.size(); }

    private String formatSize(long bytes) {
        if (bytes < 1024 * 1024) return (bytes / 1024) + " KB";
        return String.format("%.1f MB", bytes / (1024.0 * 1024.0));
    }

    static class ViewHolder extends RecyclerView.ViewHolder {
        final ItemVideoBinding binding;
        ViewHolder(ItemVideoBinding b) {
            super(b.getRoot());
            binding = b;
        }
    }
}
