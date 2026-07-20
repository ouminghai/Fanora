import assert from "node:assert/strict";
import test from "node:test";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";

import {
  HeroJoinButton,
  HeroView,
  shouldShowHeroJoinButton,
} from "../components/homes/home/Hero";

function renderHero() {
  return renderToStaticMarkup(<HeroView status="initializing" hasUser={false} />);
}

test("hero applies sequential typewriter hooks to both headline lines", () => {
  const markup = renderHero();
  const typewriterHooks = markup.match(/data-hero-typewriter="true"/g) || [];

  assert.equal(typewriterHooks.length, 2);
  assert.match(markup, /hero-typewriter--1/);
  assert.match(markup, /hero-typewriter--2/);
});

test("hero keeps staggered fade-up hooks on content that is always visible", () => {
  const markup = renderHero();
  const revealHooks = markup.match(/data-hero-reveal="true"/g) || [];

  assert.equal(revealHooks.length, 2);
  assert.match(markup, /hero-reveal--3/);
  assert.match(markup, /hero-reveal--5/);
});

test("hero join button points to login and only appears for anonymous users", () => {
  const markup = renderToStaticMarkup(<HeroJoinButton />);
  const anonymousHero = renderToStaticMarkup(
    <HeroView status="anonymous" hasUser={false} />,
  );
  const initializingHero = renderToStaticMarkup(
    <HeroView status="initializing" hasUser={false} />,
  );
  const authenticatedHero = renderToStaticMarkup(
    <HeroView status="authenticated" hasUser />,
  );

  assert.match(markup, /href="\/login"/);
  assert.match(markup, /hero-reveal--4/);
  assert.match(anonymousHero, /href="\/login"/);
  assert.doesNotMatch(initializingHero, /href="\/login"/);
  assert.doesNotMatch(authenticatedHero, /href="\/login"/);
  assert.equal(shouldShowHeroJoinButton("anonymous", false), true);
  assert.equal(shouldShowHeroJoinButton("error", false), true);
  assert.equal(shouldShowHeroJoinButton("initializing", false), false);
  assert.equal(shouldShowHeroJoinButton("connecting", false), false);
  assert.equal(shouldShowHeroJoinButton("authenticated", true), false);
});
