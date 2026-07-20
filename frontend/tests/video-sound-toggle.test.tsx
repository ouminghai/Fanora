import assert from "node:assert/strict";
import test from "node:test";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { VideoSoundToggle } from "../components/headers/Header3";
import { HeroView } from "../components/homes/home/Hero";

test("video sound toggle starts muted and exposes an accessible icon button", () => {
  const markup = renderToStaticMarkup(<VideoSoundToggle />);

  assert.match(markup, /data-video-sound-toggle="true"/);
  assert.match(markup, /aria-label="打开视频声音"/);
  assert.match(markup, /aria-pressed="false"/);
});

test("hero video starts muted so browser autoplay remains available", () => {
  const markup = renderToStaticMarkup(
    <HeroView status="initializing" hasUser={false} />,
  );

  assert.match(markup, /<video[^>]*muted=""/);
  assert.doesNotMatch(markup, />开启视频声音</);
});
