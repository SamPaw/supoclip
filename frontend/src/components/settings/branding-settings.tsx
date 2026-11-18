"use client";

import { useState, useEffect, useRef } from "react";
import {
  Music,
  Film,
  Upload,
  Trash2,
  Loader2,
  Volume2,
  AlertCircle,
  Clock,
  Sparkles,
} from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Slider } from "@/components/ui/slider";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";

export type BackgroundMusicData = {
  enabled: boolean;
  path: string;
  filename: string;
  volume: number;
  url?: string;
};

export type OutroVideoData = {
  enabled: boolean;
  path: string;
  filename: string;
  duration: number;
  url?: string;
};

export function BrandingSettingsSection() {
  const [bgm, setBgm] = useState<BackgroundMusicData | null>(null);
  const [outro, setOutro] = useState<OutroVideoData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isUploadingBgm, setIsUploadingBgm] = useState(false);
  const [isUploadingOutro, setIsUploadingOutro] = useState(false);

  const bgmInputRef = useRef<HTMLInputElement>(null);
  const outroInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    fetchBranding();
  }, []);

  async function fetchBranding() {
    try {
      setIsLoading(true);
      const res = await fetch("/api/branding", { cache: "no-store" });
      if (res.ok) {
        const data = await res.json();
        setBgm(data.backgroundMusic || null);
        setOutro(data.outroVideo || null);
      }
    } catch (err) {
      console.error("Failed to fetch branding:", err);
    } finally {
      setIsLoading(false);
    }
  }

  // Handle Background Music Upload
  async function handleBgmChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    const allowed = [".mp3", ".wav", ".m4a", ".aac", ".ogg"];
    const ext = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();
    if (!allowed.includes(ext)) {
      toast.error(`Please select a supported audio file (${allowed.join(", ")})`);
      return;
    }

    try {
      setIsUploadingBgm(true);
      const formData = new FormData();
      formData.append("file", file);

      const res = await fetch("/api/branding/background-music", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Failed to upload background music");
      }

      const data = await res.json();
      setBgm(data.backgroundMusic);
      toast.success("Background music uploaded and set for all future clips!");
    } catch (err: any) {
      toast.error(err.message || "Failed to upload background music");
    } finally {
      setIsUploadingBgm(false);
      if (bgmInputRef.current) bgmInputRef.current.value = "";
    }
  }

  // Handle Outro Video Upload with Client-side Duration Check
  async function handleOutroChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    const allowed = [".mp4", ".mov", ".webm", ".m4v"];
    const ext = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();
    if (!allowed.includes(ext)) {
      toast.error(`Please select a supported video file (${allowed.join(", ")})`);
      return;
    }

    // Client-side duration verification before uploading
    const objectUrl = URL.createObjectURL(file);
    const videoElem = document.createElement("video");
    videoElem.preload = "metadata";

    videoElem.onloadedmetadata = async () => {
      URL.revokeObjectURL(objectUrl);
      const duration = videoElem.duration;

      if (duration > 5.05) {
        toast.error(
          `Outro video must be 5 seconds or less (selected video is ${duration.toFixed(1)}s)`
        );
        if (outroInputRef.current) outroInputRef.current.value = "";
        return;
      }

      try {
        setIsUploadingOutro(true);
        const formData = new FormData();
        formData.append("file", file);

        const res = await fetch("/api/branding/outro-video", {
          method: "POST",
          body: formData,
        });

        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          throw new Error(err.detail || "Failed to upload outro video");
        }

        const data = await res.json();
        setOutro(data.outroVideo);
        toast.success("Outro video uploaded and set for all future clips!");
      } catch (err: any) {
        toast.error(err.message || "Failed to upload outro video");
      } finally {
        setIsUploadingOutro(false);
        if (outroInputRef.current) outroInputRef.current.value = "";
      }
    };

    videoElem.onerror = () => {
      URL.revokeObjectURL(objectUrl);
      toast.error("Could not read video metadata. Please select a valid video file.");
      if (outroInputRef.current) outroInputRef.current.value = "";
    };

    videoElem.src = objectUrl;
  }

  // Delete handlers
  async function handleDeleteBgm() {
    try {
      const res = await fetch("/api/branding/background-music", { method: "DELETE" });
      if (res.ok) {
        setBgm(null);
        toast.success("Background music removed");
      }
    } catch {
      toast.error("Failed to remove background music");
    }
  }

  async function handleDeleteOutro() {
    try {
      const res = await fetch("/api/branding/outro-video", { method: "DELETE" });
      if (res.ok) {
        setOutro(null);
        toast.success("Outro video removed");
      }
    } catch {
      toast.error("Failed to remove outro video");
    }
  }

  // Update Settings (Toggle enable or volume)
  async function updateSettings(updates: {
    backgroundMusic?: { enabled?: boolean; volume?: number };
    outroVideo?: { enabled?: boolean };
  }) {
    try {
      const res = await fetch("/api/branding/settings", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(updates),
      });
      if (res.ok) {
        const data = await res.json();
        if (data.backgroundMusic) setBgm(data.backgroundMusic);
        if (data.outroVideo) setOutro(data.outroVideo);
      }
    } catch {
      toast.error("Failed to update branding settings");
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-8 text-sm text-muted-foreground">
        <Loader2 className="size-4 animate-spin mr-2" />
        Loading branding assets...
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Background Music Card */}
      <div className="rounded-xl border bg-card p-5 space-y-4">
        <div className="flex items-start justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <div className="flex size-7 items-center justify-center rounded-lg bg-indigo-500/10 text-indigo-500">
                <Music className="size-4" />
              </div>
              <h3 className="font-semibold text-sm">Background Music</h3>
              {bgm && (
                <Badge variant={bgm.enabled ? "default" : "secondary"} className="text-xs">
                  {bgm.enabled ? "Active" : "Disabled"}
                </Badge>
              )}
            </div>
            <p className="text-xs text-muted-foreground">
              Automatically mixed behind speech on all clips. Persists across all future sessions.
            </p>
          </div>

          {bgm && (
            <div className="flex items-center gap-2">
              <Switch
                checked={bgm.enabled}
                onCheckedChange={(checked) => {
                  setBgm({ ...bgm, enabled: checked });
                  updateSettings({ backgroundMusic: { enabled: checked } });
                }}
                aria-label="Toggle background music"
              />
            </div>
          )}
        </div>

        {bgm ? (
          <div className="space-y-4 rounded-lg bg-muted/40 p-4 border">
            <div className="flex items-center justify-between text-xs">
              <span className="font-medium truncate max-w-[280px]">{bgm.filename}</span>
              <Button
                variant="ghost"
                size="sm"
                className="h-7 text-destructive hover:bg-destructive/10 hover:text-destructive"
                onClick={handleDeleteBgm}
              >
                <Trash2 className="size-3.5 mr-1" />
                Remove
              </Button>
            </div>

            {/* Audio player preview */}
            <audio
              controls
              src="/api/branding/file?type=bgm"
              className="w-full h-8"
              preload="metadata"
            />

            {/* Volume Slider */}
            <div className="space-y-2 pt-1">
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span className="flex items-center gap-1.5 font-medium">
                  <Volume2 className="size-3.5" />
                  Music Volume (relative to dialogue)
                </span>
                <span className="tabular-nums font-semibold text-foreground">
                  {Math.round((bgm.volume ?? 0.15) * 100)}%
                </span>
              </div>
              <Slider
                value={[(bgm.volume ?? 0.15) * 100]}
                min={5}
                max={60}
                step={5}
                onValueChange={(val) => {
                  const vol = val[0] / 100;
                  setBgm({ ...bgm, volume: vol });
                }}
                onValueCommit={(val) => {
                  const vol = val[0] / 100;
                  updateSettings({ backgroundMusic: { volume: vol } });
                }}
              />
              <p className="text-[11px] text-muted-foreground">
                Recommended: 10%–20% so spoken dialogue remains completely clear.
              </p>
            </div>

            <div className="pt-1">
              <Button
                variant="outline"
                size="sm"
                className="text-xs h-8"
                onClick={() => bgmInputRef.current?.click()}
                disabled={isUploadingBgm}
              >
                {isUploadingBgm ? (
                  <Loader2 className="size-3.5 animate-spin mr-1.5" />
                ) : (
                  <Upload className="size-3.5 mr-1.5" />
                )}
                Replace Music
              </Button>
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center rounded-lg border-2 border-dashed border-border/80 p-6 text-center hover:bg-muted/30 transition-colors">
            <div className="flex size-10 items-center justify-center rounded-full bg-muted mb-2">
              <Music className="size-5 text-muted-foreground" />
            </div>
            <p className="text-xs font-medium">No background music configured</p>
            <p className="text-[11px] text-muted-foreground mt-0.5 mb-3">
              Supports MP3, WAV, M4A, AAC. Automatically loops to match clip duration.
            </p>
            <Button
              size="sm"
              variant="outline"
              onClick={() => bgmInputRef.current?.click()}
              disabled={isUploadingBgm}
            >
              {isUploadingBgm ? (
                <>
                  <Loader2 className="size-3.5 animate-spin mr-2" />
                  Uploading...
                </>
              ) : (
                <>
                  <Upload className="size-3.5 mr-2" />
                  Upload Background Music
                </>
              )}
            </Button>
          </div>
        )}

        <input
          ref={bgmInputRef}
          type="file"
          accept="audio/*,.mp3,.wav,.m4a,.aac,.ogg"
          className="hidden"
          onChange={handleBgmChange}
        />
      </div>

      {/* Outro Video Card */}
      <div className="rounded-xl border bg-card p-5 space-y-4">
        <div className="flex items-start justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <div className="flex size-7 items-center justify-center rounded-lg bg-pink-500/10 text-pink-500">
                <Film className="size-4" />
              </div>
              <h3 className="font-semibold text-sm">Outro Video</h3>
              {outro && (
                <Badge variant={outro.enabled ? "default" : "secondary"} className="text-xs">
                  {outro.enabled ? "Active" : "Disabled"}
                </Badge>
              )}
            </div>
            <p className="text-xs text-muted-foreground">
              Appended to the end of every clip (calls to action, logo sting, social handle). Maximum duration:{" "}
              <strong className="text-foreground font-semibold">5 seconds</strong>.
            </p>
          </div>

          {outro && (
            <div className="flex items-center gap-2">
              <Switch
                checked={outro.enabled}
                onCheckedChange={(checked) => {
                  setOutro({ ...outro, enabled: checked });
                  updateSettings({ outroVideo: { enabled: checked } });
                }}
                aria-label="Toggle outro video"
              />
            </div>
          )}
        </div>

        {outro ? (
          <div className="space-y-4 rounded-lg bg-muted/40 p-4 border">
            <div className="flex items-center justify-between text-xs">
              <div className="flex items-center gap-2">
                <span className="font-medium truncate max-w-[200px]">{outro.filename}</span>
                <Badge variant="outline" className="text-[10px] tabular-nums flex items-center gap-1">
                  <Clock className="size-2.5" />
                  {outro.duration}s
                </Badge>
              </div>
              <Button
                variant="ghost"
                size="sm"
                className="h-7 text-destructive hover:bg-destructive/10 hover:text-destructive"
                onClick={handleDeleteOutro}
              >
                <Trash2 className="size-3.5 mr-1" />
                Remove
              </Button>
            </div>

            {/* Video preview */}
            <div className="flex justify-center bg-black/50 rounded-lg p-2 overflow-hidden max-h-52">
              <video
                controls
                src="/api/branding/file?type=outro"
                className="max-h-48 rounded object-contain"
                preload="metadata"
              />
            </div>

            <div className="pt-1">
              <Button
                variant="outline"
                size="sm"
                className="text-xs h-8"
                onClick={() => outroInputRef.current?.click()}
                disabled={isUploadingOutro}
              >
                {isUploadingOutro ? (
                  <Loader2 className="size-3.5 animate-spin mr-1.5" />
                ) : (
                  <Upload className="size-3.5 mr-1.5" />
                )}
                Replace Outro Video
              </Button>
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center rounded-lg border-2 border-dashed border-border/80 p-6 text-center hover:bg-muted/30 transition-colors">
            <div className="flex size-10 items-center justify-center rounded-full bg-muted mb-2">
              <Film className="size-5 text-muted-foreground" />
            </div>
            <p className="text-xs font-medium">No outro video configured</p>
            <p className="text-[11px] text-muted-foreground mt-0.5 mb-3">
              MP4, MOV, or WEBM. Must be <strong>5 seconds or less</strong>.
            </p>
            <Button
              size="sm"
              variant="outline"
              onClick={() => outroInputRef.current?.click()}
              disabled={isUploadingOutro}
            >
              {isUploadingOutro ? (
                <>
                  <Loader2 className="size-3.5 animate-spin mr-2" />
                  Uploading...
                </>
              ) : (
                <>
                  <Upload className="size-3.5 mr-2" />
                  Upload Outro Video (Max 5s)
                </>
              )}
            </Button>
          </div>
        )}

        <input
          ref={outroInputRef}
          type="file"
          accept="video/*,.mp4,.mov,.webm,.m4v"
          className="hidden"
          onChange={handleOutroChange}
        />
      </div>
    </div>
  );
}
