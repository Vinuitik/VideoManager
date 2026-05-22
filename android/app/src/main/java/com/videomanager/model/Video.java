package com.videomanager.model;

import com.google.gson.annotations.SerializedName;

public class Video {
    public String name;
    public long size;
    @SerializedName("modified_at")
    public String modifiedAt;
}
