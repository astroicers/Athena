// Copyright 2026 Athena Contributors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

"use client";

import { useRef, useState, useCallback, useEffect } from "react";

interface VirtualListProps<T> {
  items: T[];
  rowHeight: number;
  height: number;
  renderRow: (item: T, index: number) => React.ReactNode;
  className?: string;
}

export function VirtualList<T>({
  items,
  rowHeight,
  height,
  renderRow,
  className = "",
}: VirtualListProps<T>) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [scrollTop, setScrollTop] = useState(0);

  const handleScroll = useCallback(() => {
    if (containerRef.current) {
      setScrollTop(containerRef.current.scrollTop);
    }
  }, []);

  // Auto-scroll to bottom when new items are added
  const prevLengthRef = useRef(items.length);
  useEffect(() => {
    if (items.length > prevLengthRef.current && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
    prevLengthRef.current = items.length;
  }, [items.length]);

  const totalHeight = items.length * rowHeight;
  const buffer = 5;
  const startIndex = Math.max(0, Math.floor(scrollTop / rowHeight) - buffer);
  const visibleCount = Math.ceil(height / rowHeight) + buffer * 2;
  const endIndex = Math.min(items.length, startIndex + visibleCount);

  return (
    <div
      ref={containerRef}
      onScroll={handleScroll}
      className={`overflow-y-auto ${className}`}
      style={{ height, position: "relative" }}
    >
      <div style={{ height: totalHeight, position: "relative" }}>
        {items.slice(startIndex, endIndex).map((item, i) => (
          <div
            key={startIndex + i}
            style={{
              position: "absolute",
              top: (startIndex + i) * rowHeight,
              left: 0,
              right: 0,
              height: rowHeight,
            }}
          >
            {renderRow(item, startIndex + i)}
          </div>
        ))}
      </div>
    </div>
  );
}
