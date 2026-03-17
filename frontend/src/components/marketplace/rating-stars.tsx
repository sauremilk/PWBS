"use client";

import { Star } from "lucide-react";
import { useState } from "react";

interface RatingStarsProps {
  value: number;
  onChange?: (value: number) => void;
  size?: "sm" | "md";
  readonly?: boolean;
}

export function RatingStars({
  value,
  onChange,
  size = "md",
  readonly = false,
}: RatingStarsProps) {
  const [hover, setHover] = useState(0);
  const iconSize = size === "sm" ? "h-4 w-4" : "h-5 w-5";

  return (
    <div className="inline-flex gap-0.5" role="group" aria-label="Bewertung">
      {[1, 2, 3, 4, 5].map((star) => {
        const filled = star <= (hover || value);
        return (
          <button
            key={star}
            type="button"
            disabled={readonly}
            onClick={() => onChange?.(star)}
            onMouseEnter={() => !readonly && setHover(star)}
            onMouseLeave={() => !readonly && setHover(0)}
            className={`${readonly ? "cursor-default" : "cursor-pointer"} focus:outline-none`}
            aria-label={`${star} Stern${star > 1 ? "e" : ""}`}
          >
            <Star
              aria-hidden="true"
              className={`${iconSize} ${
                filled
                  ? "fill-yellow-400 text-yellow-400"
                  : "fill-none text-gray-300"
              }`}
            />
          </button>
        );
      })}
    </div>
  );
}

export function AverageRating({
  ratingSum,
  ratingCount,
}: {
  ratingSum: number;
  ratingCount: number;
}) {
  const avg = ratingCount > 0 ? ratingSum / ratingCount : 0;
  return (
    <div className="flex items-center gap-1.5">
      <RatingStars value={Math.round(avg)} readonly size="sm" />
      <span className="text-sm text-text-secondary">
        {avg > 0 ? avg.toFixed(1) : "–"} ({ratingCount})
      </span>
    </div>
  );
}
