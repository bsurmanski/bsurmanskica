---
title: "Gaming Log"
description: "Micro-reviews and completion statuses for retro and modern titles."
layout: "game-archive"
---

{{ $user := "branOwl" }}
{{ $key := "gYodDJDDZUXZGhXvvFSjqCQot4wcoA2X" }}
{{ if and $user $key }}
  {{ $url := printf "https://retroachievements.org/API/API_GetUserSummary.php?z=%s&y=%s&u=%s" $user $key $user }}
  {{ with resources.GetRemote $url }}
    {{ with .Err }}
      <p>Error fetching RA stats: {{ . }}</p>
    {{ else }}
      {{ $data := .Content | transform.Unmarshal }}
      <div class="ra-widget" style="border: 1px solid #ddd; padding: 15px; border-radius: 8px; display: flex; align-items: center; gap: 15px;">
        <img src="https://retroachievements.org{{ $data.UserPic }}" alt="{{ $user }}" style="width: 60px; height: 60px; border-radius: 50%;">
        <div>
          <h4 style="margin: 0;">{{ $user }}</h4>
          <p style="margin: 0; font-size: 0.9em;">Points: <strong>{{ $data.TotalPoints }}</strong> | Ratio: {{ $data.TotalTruePoints }}</p>
          <p style="margin: 0; font-size: 0.8em;">Recently: <em>{{ (index $data.RecentlyPlayed 0).Title }}</em></p>
        </div>
      </div>
    {{ end }}
  {{ end }}
{{ end }}
