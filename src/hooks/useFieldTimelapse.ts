"use client";

import { useState, useMemo, useEffect, useRef, useCallback } from "react";
import { TimelapseManifest, TimelineState, TimelapseFrame, WeatherDaily, TimelapseLayer } from "@/types/terria";

export interface UseFieldTimelapseOptions {
  manifest: TimelapseManifest;
  maxImageAgeDays?: number; // Default 10 according to participant-4 spec
}

export function useFieldTimelapse({
  manifest,
  maxImageAgeDays = 10,
}: UseFieldTimelapseOptions) {
  const dates = useMemo(() => manifest.weatherDaily.map((w) => w.date), [manifest]);

  // Start at the latest usable observation by default
  const defaultIndex = useMemo(() => {
    const usableFrames = manifest.frames.filter((f) => f.usable);
    if (usableFrames.length === 0) return Math.max(0, dates.length - 1);
    const lastObservationDate = usableFrames[usableFrames.length - 1].localDate;
    const idx = dates.indexOf(lastObservationDate);
    return idx !== -1 ? idx : Math.max(0, dates.length - 1);
  }, [dates, manifest.frames]);

  const [dateIndex, setDateIndex] = useState<number>(defaultIndex);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [speed, setSpeed] = useState<1 | 2 | 4>(1);
  const [activeLayer, setActiveLayer] = useState<TimelapseLayer>("ndvi");

  const selectedDate = dates[dateIndex] || dates[0] || "";

  // Deterministic 2-clock resolver (Participant 4 spec)
  const timelineState: TimelineState = useMemo(() => {
    const weather: WeatherDaily | null =
      manifest.weatherDaily.find((w) => w.date === selectedDate) || null;

    // Find latest usable frame <= selectedDate
    const candidateFrames = manifest.frames
      .filter((f) => f.usable && f.localDate <= selectedDate)
      .sort((a, b) => b.localDate.localeCompare(a.localDate));

    const latestFrame: TimelapseFrame | null = candidateFrames[0] || null;

    if (!latestFrame) {
      return {
        selectedDate,
        weather,
        satellite: null,
        isFresh: false,
        ageDays: null,
        missingReason: "NO_PREVIOUS_OBSERVATION",
      };
    }

    const currentDateObj = new Date(selectedDate);
    const frameDateObj = new Date(latestFrame.localDate);
    const diffMs = currentDateObj.getTime() - frameDateObj.getTime();
    const ageDays = Math.max(0, Math.round(diffMs / 86400000));

    if (ageDays > maxImageAgeDays) {
      return {
        selectedDate,
        weather,
        satellite: null,
        isFresh: false,
        ageDays,
        missingReason: "MAX_IMAGE_AGE_EXCEEDED",
      };
    }

    return {
      selectedDate,
      weather,
      satellite: latestFrame,
      isFresh: true,
      ageDays,
    };
  }, [manifest, selectedDate, maxImageAgeDays]);

  // Animation ticker for playback
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  const stepNext = useCallback(() => {
    setDateIndex((prev) => (prev + 1 >= dates.length ? 0 : prev + 1));
  }, [dates.length]);

  const stepPrev = useCallback(() => {
    setDateIndex((prev) => (prev - 1 < 0 ? dates.length - 1 : prev - 1));
  }, [dates.length]);

  const jumpToObservation = useCallback(
    (direction: "prev" | "next") => {
      const usableDates = manifest.frames
        .filter((f) => f.usable)
        .map((f) => f.localDate);

      if (usableDates.length === 0) return;

      if (direction === "next") {
        const nextDate = usableDates.find((d) => d > selectedDate);
        if (nextDate) {
          const idx = dates.indexOf(nextDate);
          if (idx !== -1) setDateIndex(idx);
        }
      } else {
        const prevDates = usableDates.filter((d) => d < selectedDate);
        if (prevDates.length > 0) {
          const prevDate = prevDates[prevDates.length - 1];
          const idx = dates.indexOf(prevDate);
          if (idx !== -1) setDateIndex(idx);
        }
      }
    },
    [dates, manifest.frames, selectedDate]
  );

  useEffect(() => {
    if (!isPlaying) {
      if (intervalRef.current) clearInterval(intervalRef.current);
      return;
    }

    // Step every (1000 / speed) ms
    const intervalMs = 1000 / speed;
    intervalRef.current = setInterval(() => {
      setDateIndex((prev) => {
        if (prev + 1 >= dates.length) {
          setIsPlaying(false);
          return prev;
        }
        return prev + 1;
      });
    }, intervalMs);

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [isPlaying, speed, dates.length]);

  return {
    manifest,
    dates,
    dateIndex,
    setDateIndex,
    selectedDate,
    timelineState,
    isPlaying,
    setIsPlaying,
    speed,
    setSpeed,
    activeLayer,
    setActiveLayer,
    stepNext,
    stepPrev,
    jumpToObservation,
  };
}
