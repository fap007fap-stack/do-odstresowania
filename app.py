from __future__ import annotations

import hashlib
import re
import secrets
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import streamlit as st
import streamlit.components.v1 as components


APP_DIR = Path(__file__).parent
DB_PATH = APP_DIR / "scores.sqlite3"
FRONTEND_DIR = APP_DIR / "frontend"
FRONTEND_HTML = '<!doctype html>\n<html lang="pl">\n<head>\n  <meta charset="utf-8" />\n  <meta name="viewport" content="width=device-width, initial-scale=1" />\n  <title>Saperka vs Kurierzy</title>\n  <style>\n    :root {\n      --bg: #0d0d0f;\n      --panel: #17171b;\n      --panel2: #22222a;\n      --text: #f6f6f6;\n      --muted: rgba(255,255,255,.68);\n      --accent: #ffd21f;\n    }\n\n    html, body {\n      margin: 0;\n      padding: 0;\n      background: transparent;\n      color: var(--text);\n      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;\n      overflow: hidden;\n      touch-action: none;\n    }\n\n    #layout {\n      width: 100%;\n      height: 760px;\n      display: grid;\n      grid-template-columns: minmax(640px, 1fr) 260px;\n      gap: 12px;\n      box-sizing: border-box;\n      padding: 0;\n    }\n\n    #gameBox {\n      background: radial-gradient(circle at center, #272727 0%, #151515 70%, #080808 100%);\n      border-radius: 18px;\n      overflow: hidden;\n      position: relative;\n      box-shadow: inset 0 0 0 1px rgba(255,255,255,.08);\n    }\n\n    canvas {\n      display: block;\n      width: 100%;\n      height: 100%;\n      cursor: crosshair;\n    }\n\n    #side {\n      background: linear-gradient(180deg, var(--panel), #0f0f12);\n      border: 1px solid rgba(255,255,255,.08);\n      border-radius: 18px;\n      padding: 16px;\n      box-sizing: border-box;\n      overflow: hidden;\n    }\n\n    .label {\n      color: var(--muted);\n      font-size: 12px;\n      text-transform: uppercase;\n      letter-spacing: .08em;\n      margin-bottom: 5px;\n    }\n\n    .nick {\n      font-weight: 800;\n      font-size: 24px;\n      margin-bottom: 16px;\n      word-break: break-word;\n    }\n\n    .scorecard {\n      background: var(--panel2);\n      border: 1px solid rgba(255,255,255,.08);\n      border-radius: 14px;\n      padding: 12px;\n      margin-bottom: 14px;\n    }\n\n    .big {\n      font-size: 28px;\n      font-weight: 900;\n    }\n\n    .small {\n      font-size: 13px;\n      color: var(--muted);\n    }\n\n    h3 {\n      margin: 16px 0 10px;\n      font-size: 18px;\n    }\n\n    ol {\n      margin: 0;\n      padding-left: 0;\n      list-style: none;\n      display: grid;\n      gap: 8px;\n    }\n\n    li {\n      display: grid;\n      grid-template-columns: 28px 1fr auto;\n      gap: 8px;\n      align-items: center;\n      background: rgba(255,255,255,.055);\n      border: 1px solid rgba(255,255,255,.07);\n      border-radius: 12px;\n      padding: 9px;\n      font-size: 13px;\n    }\n\n    .place {\n      width: 24px;\n      height: 24px;\n      border-radius: 999px;\n      display: grid;\n      place-items: center;\n      background: rgba(255,255,255,.1);\n      font-weight: 800;\n    }\n\n    .score {\n      font-weight: 900;\n      color: var(--accent);\n    }\n\n    #hint {\n      position: absolute;\n      left: 12px;\n      bottom: 10px;\n      right: 12px;\n      text-align: center;\n      font-size: 13px;\n      opacity: .72;\n      pointer-events: none;\n      text-shadow: 0 1px 3px #000;\n    }\n\n    @media (max-width: 980px) {\n      #layout {\n        grid-template-columns: 1fr;\n        height: 900px;\n      }\n      #gameBox {\n        height: 660px;\n      }\n      #side {\n        height: 228px;\n      }\n    }\n  </style>\n</head>\n<body>\n  <div id="layout">\n    <div id="gameBox">\n      <canvas id="game" width="1100" height="700"></canvas>\n      <div id="hint">Sterowanie: mysz/touch = celowanie, klik/Spacja = rzut saperką, R = restart</div>\n    </div>\n    <aside id="side">\n      <div class="label">Gracz</div>\n      <div class="nick" id="nick">---</div>\n\n      <div class="scorecard">\n        <div class="label">Twój rekord</div>\n        <div class="big" id="myBest">0</div>\n        <div class="small">Zapisuje się po końcu gry</div>\n      </div>\n\n      <h3>Ranking TOP 10</h3>\n      <ol id="leaderboard"></ol>\n    </aside>\n  </div>\n\n<script>\n/* Minimalny protokół komunikacji dla Streamlit Custom Components. */\nconst StreamlitBridge = (() => {\n  const RENDER_EVENT = "streamlit:render";\n  const COMPONENT_READY = "streamlit:componentReady";\n  const SET_COMPONENT_VALUE = "streamlit:setComponentValue";\n  const SET_FRAME_HEIGHT = "streamlit:setFrameHeight";\n\n  function sendMessageToStreamlitClient(type, data) {\n    window.parent.postMessage({\n      isStreamlitMessage: true,\n      type: type,\n      ...data,\n    }, "*");\n  }\n\n  function setComponentReady() {\n    sendMessageToStreamlitClient(COMPONENT_READY, { apiVersion: 1 });\n  }\n\n  function setFrameHeight(height) {\n    sendMessageToStreamlitClient(SET_FRAME_HEIGHT, { height });\n  }\n\n  function setComponentValue(value) {\n    sendMessageToStreamlitClient(SET_COMPONENT_VALUE, {\n      value: value,\n      dataType: "json",\n    });\n  }\n\n  return {\n    RENDER_EVENT,\n    setComponentReady,\n    setFrameHeight,\n    setComponentValue,\n  };\n})();\n\nlet playerNick = "Gracz";\nlet leaderboardData = [];\nlet myBestFromServer = 0;\n\nfunction updateSidebar() {\n  document.getElementById("nick").textContent = playerNick || "Gracz";\n  document.getElementById("myBest").textContent = String(myBestFromServer || 0);\n\n  const list = document.getElementById("leaderboard");\n  list.innerHTML = "";\n\n  if (!leaderboardData || leaderboardData.length === 0) {\n    const li = document.createElement("li");\n    li.style.gridTemplateColumns = "1fr";\n    li.innerHTML = "<span class=\'small\'>Jeszcze brak wyników. Zagraj pierwszą rundę.</span>";\n    list.appendChild(li);\n    return;\n  }\n\n  leaderboardData.slice(0, 10).forEach((row, idx) => {\n    const li = document.createElement("li");\n    const place = row.place || idx + 1;\n    const nick = row.nick || "Gracz";\n    const score = row.score || 0;\n    li.innerHTML = `\n      <span class="place">${place}</span>\n      <span title="${escapeHtml(nick)}">${escapeHtml(nick)}</span>\n      <span class="score">${score}</span>\n    `;\n    list.appendChild(li);\n  });\n}\n\nfunction escapeHtml(s) {\n  return String(s).replace(/[&<>"\']/g, ch => ({\n    "&": "&amp;",\n    "<": "&lt;",\n    ">": "&gt;",\n    \'"\': "&quot;",\n    "\'": "&#039;",\n  }[ch]));\n}\n\nwindow.addEventListener("message", (event) => {\n  if (!event.data || event.data.type !== StreamlitBridge.RENDER_EVENT) return;\n\n  const args = event.data.args || {};\n  playerNick = args.nick || playerNick;\n  leaderboardData = args.leaderboard || leaderboardData || [];\n  myBestFromServer = args.my_best || myBestFromServer || 0;\n  updateSidebar();\n});\n\nStreamlitBridge.setComponentReady();\nStreamlitBridge.setFrameHeight(760);\n\n(() => {\n  const canvas = document.getElementById("game");\n  const ctx = canvas.getContext("2d");\n\n  const W = canvas.width;\n  const H = canvas.height;\n\n  const couriers = [\n    { name: "DPD", points: 20, body: "#e6e6e6", stripe: "#c8001d", text: "#222" },\n    { name: "InPost", points: 10, body: "#ffd21f", stripe: "#111", text: "#111" },\n    { name: "Poczta Polska", points: 10, body: "#fff4d0", stripe: "#d6001c", text: "#b00014" },\n    { name: "Orlen Paczka", points: 10, body: "#f5f5f5", stripe: "#e00016", text: "#111" }\n  ];\n\n  let player;\n  let shovels;\n  let cars;\n  let particles;\n  let score;\n  let lives;\n  let level;\n  let spawnTimer;\n  let gameOver;\n  let started;\n  let aimX;\n  let aimY;\n  let shake;\n  let localBest;\n  let scoreSent;\n  let roundId;\n\n  function newRoundId() {\n    return `${Date.now()}-${Math.random().toString(16).slice(2)}`;\n  }\n\n  function reset() {\n    player = { x: W / 2, y: H - 62, cooldown: 0 };\n    shovels = [];\n    cars = [];\n    particles = [];\n    score = 0;\n    lives = 5;\n    level = 1;\n    spawnTimer = 0;\n    gameOver = false;\n    started = false;\n    aimX = W / 2;\n    aimY = H / 2;\n    shake = 0;\n    localBest = Number(localStorage.getItem("saperka_best") || 0);\n    scoreSent = false;\n    roundId = newRoundId();\n  }\n\n  function rnd(min, max) {\n    return Math.random() * (max - min) + min;\n  }\n\n  function pickCourier() {\n    const bag = [couriers[0], couriers[0], couriers[1], couriers[2], couriers[3]];\n    return bag[Math.floor(Math.random() * bag.length)];\n  }\n\n  function spawnCar() {\n    const c = pickCourier();\n    const laneY = rnd(100, H - 210);\n    const fromLeft = Math.random() < 0.5;\n    const speed = rnd(2.0, 3.9) + level * 0.25;\n    cars.push({\n      x: fromLeft ? -170 : W + 170,\n      y: laneY,\n      w: 146,\n      h: 62,\n      vx: fromLeft ? speed : -speed,\n      courier: c,\n      hit: false,\n      wobble: rnd(0, Math.PI * 2)\n    });\n  }\n\n  function throwShovel() {\n    if (gameOver) {\n      reset();\n      return;\n    }\n\n    started = true;\n\n    if (player.cooldown > 0) return;\n    player.cooldown = 13;\n\n    const dx = aimX - player.x;\n    const dy = aimY - player.y;\n    const len = Math.max(1, Math.hypot(dx, dy));\n    const speed = 13.5;\n\n    shovels.push({\n      x: player.x,\n      y: player.y - 20,\n      vx: dx / len * speed,\n      vy: dy / len * speed,\n      rot: Math.atan2(dy, dx),\n      spin: 0.33,\n      life: 100\n    });\n  }\n\n  function addBurst(x, y, label, good) {\n    for (let i = 0; i < 18; i++) {\n      particles.push({\n        x, y,\n        vx: rnd(-4, 4),\n        vy: rnd(-5, 2),\n        life: rnd(22, 44),\n        size: rnd(2, 6),\n        label: null,\n        good\n      });\n    }\n    particles.push({\n      x,\n      y: y - 10,\n      vx: 0,\n      vy: -1.4,\n      life: 48,\n      size: 18,\n      label,\n      good\n    });\n  }\n\n  function rectCircleHit(rect, px, py, radius) {\n    const cx = Math.max(rect.x, Math.min(px, rect.x + rect.w));\n    const cy = Math.max(rect.y, Math.min(py, rect.y + rect.h));\n    return Math.hypot(px - cx, py - cy) < radius;\n  }\n\n  function finishGame() {\n    if (scoreSent) return;\n    scoreSent = true;\n    StreamlitBridge.setComponentValue({\n      event: "score",\n      nick: playerNick,\n      score: score,\n      round_id: roundId\n    });\n  }\n\n  function update() {\n    if (player.cooldown > 0) player.cooldown--;\n\n    if (!gameOver && started) {\n      spawnTimer--;\n      const spawnEvery = Math.max(28, 82 - level * 5);\n      if (spawnTimer <= 0) {\n        spawnCar();\n        spawnTimer = spawnEvery;\n      }\n\n      level = 1 + Math.floor(score / 120);\n    }\n\n    for (const car of cars) {\n      car.x += car.vx;\n      car.wobble += 0.1;\n    }\n\n    for (const s of shovels) {\n      s.x += s.vx;\n      s.y += s.vy;\n      s.rot += s.spin;\n      s.life--;\n    }\n\n    for (const p of particles) {\n      p.x += p.vx;\n      p.y += p.vy;\n      p.vy += 0.11;\n      p.life--;\n    }\n\n    for (const car of cars) {\n      if (car.hit) continue;\n\n      for (const s of shovels) {\n        if (s.life <= 0) continue;\n        if (rectCircleHit(car, s.x, s.y, 18)) {\n          car.hit = true;\n          s.life = 0;\n          score += car.courier.points;\n          localBest = Math.max(localBest, score, myBestFromServer || 0);\n          localStorage.setItem("saperka_best", String(localBest));\n          addBurst(\n            car.x + car.w / 2,\n            car.y + car.h / 2,\n            `+${car.courier.points} ${car.courier.name}`,\n            true\n          );\n          shake = 7;\n          break;\n        }\n      }\n    }\n\n    const before = lives;\n    cars = cars.filter(car => {\n      if (car.hit) return false;\n      const gone = (car.vx > 0 && car.x > W + 190) || (car.vx < 0 && car.x < -210);\n      if (gone && started && !gameOver) {\n        lives--;\n        addBurst(car.vx > 0 ? W - 70 : 70, car.y + 25, "-1 życie", false);\n      }\n      return !gone;\n    });\n\n    if (before !== lives) shake = 5;\n    if (lives <= 0 && !gameOver) {\n      gameOver = true;\n      finishGame();\n    }\n\n    shovels = shovels.filter(s =>\n      s.life > 0 && s.x > -70 && s.x < W + 70 && s.y > -80 && s.y < H + 80\n    );\n    particles = particles.filter(p => p.life > 0);\n\n    if (shake > 0) shake *= 0.83;\n  }\n\n  function drawRoad() {\n    ctx.fillStyle = "#242424";\n    ctx.fillRect(0, 70, W, H - 170);\n\n    ctx.strokeStyle = "rgba(255,255,255,.18)";\n    ctx.lineWidth = 4;\n    ctx.setLineDash([34, 30]);\n\n    for (let y = 150; y < H - 170; y += 96) {\n      ctx.beginPath();\n      ctx.moveTo(0, y);\n      ctx.lineTo(W, y);\n      ctx.stroke();\n    }\n\n    ctx.setLineDash([]);\n    ctx.fillStyle = "#171717";\n    ctx.fillRect(0, 0, W, 70);\n    ctx.fillRect(0, H - 100, W, 100);\n  }\n\n  function roundRect(x, y, w, h, r) {\n    ctx.beginPath();\n    ctx.moveTo(x + r, y);\n    ctx.arcTo(x + w, y, x + w, y + h, r);\n    ctx.arcTo(x + w, y + h, x, y + h, r);\n    ctx.arcTo(x, y + h, x, y, r);\n    ctx.arcTo(x, y, x + r, y, r);\n    ctx.closePath();\n  }\n\n  function drawCar(car) {\n    const c = car.courier;\n    const flip = car.vx < 0;\n    const x = car.x;\n    const y = car.y + Math.sin(car.wobble) * 2;\n\n    ctx.save();\n\n    ctx.fillStyle = "rgba(0,0,0,.35)";\n    roundRect(x + 8, y + car.h - 3, car.w - 16, 14, 8);\n    ctx.fill();\n\n    ctx.fillStyle = c.body;\n    roundRect(x, y + 9, car.w, car.h - 13, 13);\n    ctx.fill();\n\n    ctx.fillStyle = c.body;\n    roundRect(flip ? x + 10 : x + car.w - 58, y, 55, 39, 10);\n    ctx.fill();\n\n    ctx.fillStyle = c.stripe;\n    ctx.fillRect(x + 10, y + 32, car.w - 20, 12);\n\n    ctx.fillStyle = "rgba(60,160,220,.75)";\n    roundRect(flip ? x + 19 : x + car.w - 47, y + 8, 30, 21, 5);\n    ctx.fill();\n\n    ctx.fillStyle = "#111";\n    ctx.beginPath();\n    ctx.arc(x + 32, y + car.h - 2, 13, 0, Math.PI * 2);\n    ctx.arc(x + car.w - 31, y + car.h - 2, 13, 0, Math.PI * 2);\n    ctx.fill();\n\n    ctx.fillStyle = "#777";\n    ctx.beginPath();\n    ctx.arc(x + 32, y + car.h - 2, 5, 0, Math.PI * 2);\n    ctx.arc(x + car.w - 31, y + car.h - 2, 5, 0, Math.PI * 2);\n    ctx.fill();\n\n    ctx.fillStyle = c.text;\n    ctx.font = c.name === "Poczta Polska" ? "bold 15px system-ui" : "bold 22px system-ui";\n    ctx.textAlign = "center";\n    ctx.textBaseline = "middle";\n    ctx.fillText(c.name, x + car.w / 2, y + 25);\n\n    if (c.name === "DPD") {\n      ctx.fillStyle = "#c8001d";\n      ctx.font = "bold 12px system-ui";\n      ctx.fillText("x2 pkt", x + car.w / 2, y + 47);\n    }\n\n    ctx.restore();\n  }\n\n  function drawShovel(s) {\n    ctx.save();\n    ctx.translate(s.x, s.y);\n    ctx.rotate(s.rot + Math.PI / 2);\n\n    ctx.strokeStyle = "#8b5a2b";\n    ctx.lineWidth = 6;\n    ctx.lineCap = "round";\n    ctx.beginPath();\n    ctx.moveTo(0, 18);\n    ctx.lineTo(0, -26);\n    ctx.stroke();\n\n    ctx.strokeStyle = "#d6a15b";\n    ctx.lineWidth = 4;\n    ctx.beginPath();\n    ctx.arc(0, 24, 9, 0, Math.PI * 2);\n    ctx.stroke();\n\n    ctx.fillStyle = "#b9c0c7";\n    ctx.strokeStyle = "#6f7a84";\n    ctx.lineWidth = 2;\n    ctx.beginPath();\n    ctx.moveTo(-13, -28);\n    ctx.quadraticCurveTo(0, -47, 13, -28);\n    ctx.lineTo(8, -10);\n    ctx.lineTo(-8, -10);\n    ctx.closePath();\n    ctx.fill();\n    ctx.stroke();\n\n    ctx.restore();\n  }\n\n  function drawPlayer() {\n    const x = player.x;\n    const y = player.y;\n\n    ctx.strokeStyle = "rgba(255,255,255,.35)";\n    ctx.lineWidth = 2;\n    ctx.beginPath();\n    ctx.moveTo(x, y - 25);\n    ctx.lineTo(aimX, aimY);\n    ctx.stroke();\n\n    ctx.save();\n    ctx.translate(x, y);\n\n    ctx.fillStyle = "#eee";\n    ctx.beginPath();\n    ctx.arc(0, -28, 17, 0, Math.PI * 2);\n    ctx.fill();\n\n    ctx.fillStyle = "#2d7";\n    roundRect(-18, -12, 36, 42, 12);\n    ctx.fill();\n\n    ctx.strokeStyle = "#eee";\n    ctx.lineWidth = 8;\n    ctx.lineCap = "round";\n    ctx.beginPath();\n    ctx.moveTo(-12, 22);\n    ctx.lineTo(-20, 45);\n    ctx.moveTo(12, 22);\n    ctx.lineTo(20, 45);\n    ctx.stroke();\n\n    ctx.restore();\n  }\n\n  function drawParticles() {\n    for (const p of particles) {\n      const alpha = Math.max(0, p.life / 48);\n      if (p.label) {\n        ctx.globalAlpha = alpha;\n        ctx.font = "bold 22px system-ui";\n        ctx.textAlign = "center";\n        ctx.textBaseline = "middle";\n        ctx.fillStyle = p.good ? "#fff" : "#ffb4b4";\n        ctx.strokeStyle = "rgba(0,0,0,.75)";\n        ctx.lineWidth = 4;\n        ctx.strokeText(p.label, p.x, p.y);\n        ctx.fillText(p.label, p.x, p.y);\n        ctx.globalAlpha = 1;\n      } else {\n        ctx.globalAlpha = alpha;\n        ctx.fillStyle = p.good ? "#f5f5f5" : "#ff6b6b";\n        ctx.beginPath();\n        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);\n        ctx.fill();\n        ctx.globalAlpha = 1;\n      }\n    }\n  }\n\n  function drawHud() {\n    ctx.fillStyle = "#fff";\n    ctx.font = "bold 26px system-ui";\n    ctx.textAlign = "left";\n    ctx.textBaseline = "middle";\n    ctx.fillText(`Punkty: ${score}`, 24, 35);\n\n    ctx.font = "18px system-ui";\n    ctx.fillText(`Rekord: ${Math.max(localBest, myBestFromServer || 0)}`, 190, 36);\n    ctx.fillText(`Poziom: ${level}`, 340, 36);\n\n    ctx.textAlign = "right";\n    ctx.fillText(`Życia: ${"❤".repeat(Math.max(0, lives))}`, W - 24, 36);\n\n    ctx.textAlign = "center";\n    ctx.font = "bold 16px system-ui";\n    ctx.fillStyle = "rgba(255,255,255,.75)";\n    ctx.fillText("DPD = 20 pkt, reszta = 10 pkt", W / 2, 36);\n  }\n\n  function drawStartOrGameOver() {\n    if (!started && !gameOver) {\n      ctx.fillStyle = "rgba(0,0,0,.45)";\n      ctx.fillRect(0, 0, W, H);\n\n      ctx.fillStyle = "#fff";\n      ctx.textAlign = "center";\n      ctx.textBaseline = "middle";\n      ctx.font = "bold 54px system-ui";\n      ctx.fillText("Saperka vs Kurierzy", W / 2, H / 2 - 80);\n\n      ctx.font = "22px system-ui";\n      ctx.fillText(`Gracz: ${playerNick}`, W / 2, H / 2 - 26);\n\n      ctx.font = "20px system-ui";\n      ctx.fillText("Kliknij albo naciśnij Spację, żeby rzucić saperką", W / 2, H / 2 + 22);\n\n      ctx.font = "17px system-ui";\n      ctx.fillStyle = "rgba(255,255,255,.78)";\n      ctx.fillText("Po końcu gry wynik sam zapisze się w rankingu.", W / 2, H / 2 + 62);\n    }\n\n    if (gameOver) {\n      ctx.fillStyle = "rgba(0,0,0,.58)";\n      ctx.fillRect(0, 0, W, H);\n\n      ctx.fillStyle = "#fff";\n      ctx.textAlign = "center";\n      ctx.textBaseline = "middle";\n      ctx.font = "bold 58px system-ui";\n      ctx.fillText("Koniec gry", W / 2, H / 2 - 82);\n\n      ctx.font = "bold 30px system-ui";\n      ctx.fillText(`Wynik zapisany: ${score}`, W / 2, H / 2 - 28);\n\n      ctx.font = "20px system-ui";\n      ctx.fillText("Kliknij, Spacja albo R, żeby zagrać jeszcze raz", W / 2, H / 2 + 30);\n\n      ctx.font = "16px system-ui";\n      ctx.fillStyle = "rgba(255,255,255,.75)";\n      ctx.fillText("Ranking odświeży się po chwili.", W / 2, H / 2 + 68);\n    }\n  }\n\n  function render() {\n    ctx.save();\n\n    if (shake > 0.4) {\n      ctx.translate(rnd(-shake, shake), rnd(-shake, shake));\n    }\n\n    ctx.clearRect(0, 0, W, H);\n    drawRoad();\n\n    for (const car of cars) drawCar(car);\n    for (const s of shovels) drawShovel(s);\n    drawPlayer();\n    drawParticles();\n    drawHud();\n    drawStartOrGameOver();\n\n    ctx.restore();\n  }\n\n  function loop() {\n    update();\n    render();\n    requestAnimationFrame(loop);\n  }\n\n  function pointerToCanvas(e) {\n    const rect = canvas.getBoundingClientRect();\n    const clientX = e.touches ? e.touches[0].clientX : e.clientX;\n    const clientY = e.touches ? e.touches[0].clientY : e.clientY;\n    aimX = (clientX - rect.left) / rect.width * W;\n    aimY = (clientY - rect.top) / rect.height * H;\n  }\n\n  canvas.addEventListener("mousemove", pointerToCanvas);\n  canvas.addEventListener("touchmove", e => {\n    e.preventDefault();\n    pointerToCanvas(e);\n  }, { passive: false });\n\n  canvas.addEventListener("mousedown", e => {\n    pointerToCanvas(e);\n    throwShovel();\n  });\n\n  canvas.addEventListener("touchstart", e => {\n    e.preventDefault();\n    pointerToCanvas(e);\n    throwShovel();\n  }, { passive: false });\n\n  window.addEventListener("keydown", e => {\n    if (e.code === "Space") {\n      e.preventDefault();\n      throwShovel();\n    }\n    if (e.key.toLowerCase() === "r") reset();\n  });\n\n  reset();\n  loop();\n})();\n</script>\n</body>\n</html>\n'

# Streamlit Cloud wywala błąd, jeśli folder komponentu nie istnieje w repo.
# Ta wersja tworzy go automatycznie przy starcie, więc wystarczy wrzucić samo app.py.
FRONTEND_DIR.mkdir(parents=True, exist_ok=True)
(FRONTEND_DIR / "index.html").write_text(FRONTEND_HTML, encoding="utf-8")

# W produkcji ustaw w Streamlit Secrets:
# IP_HASH_SALT = "dlugi-losowy-sekret"
DEFAULT_SALT = "zmien-ten-sekret-w-streamlit-secrets"


st.set_page_config(
    page_title="Saperka vs Kurierzy",
    page_icon="🪖",
    layout="wide",
    initial_sidebar_state="collapsed",
)

_game_component = components.declare_component(
    "saperka_game",
    path=str(FRONTEND_DIR),
)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def get_secret_salt() -> str:
    try:
        return str(st.secrets.get("IP_HASH_SALT", DEFAULT_SALT))
    except Exception:
        return DEFAULT_SALT


def get_client_ip() -> str | None:
    """Zwraca IP połączenia, jeśli Streamlit je udostępnia.

    Streamlit ostrzega, że IP nie powinno być używane do zabezpieczeń, bo da się je podszyć.
    Tutaj używamy go tylko do przypisania nicku i rankingu.
    """
    try:
        ip = getattr(st.context, "ip_address", None)
        if ip:
            return str(ip)
    except Exception:
        pass

    try:
        headers = st.context.headers
        for key in ("cf-connecting-ip", "x-real-ip", "x-forwarded-for", "x-client-ip"):
            value = headers.get(key)
            if value:
                return str(value).split(",")[0].strip()
    except Exception:
        pass

    return None


def get_visitor_key() -> tuple[str, bool]:
    ip = get_client_ip()
    salt = get_secret_salt()

    if ip:
        digest = hashlib.sha256(f"{salt}:{ip}".encode("utf-8")).hexdigest()
        return digest, True

    # Fallback dla localhost albo hostingu, który nie przekazuje IP.
    # To nie jest stałe między przeglądarkami, ale pozwala testować lokalnie.
    if "fallback_visitor_key" not in st.session_state:
        st.session_state.fallback_visitor_key = "session_" + secrets.token_hex(16)
    return st.session_state.fallback_visitor_key, False


def clean_nick(raw: str) -> str:
    nick = raw.strip()
    nick = re.sub(r"\s+", " ", nick)
    # Zostawiamy polskie znaki, litery, cyfry, spację, _ i -
    nick = re.sub(r"[^0-9A-Za-zĄĆĘŁŃÓŚŹŻąćęłńóśźż _-]", "", nick)
    return nick[:24]


def init_db() -> None:
    with sqlite3.connect(DB_PATH, timeout=30) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS players (
                visitor_key TEXT PRIMARY KEY,
                nick TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                visitor_key TEXT NOT NULL,
                nick TEXT NOT NULL,
                score INTEGER NOT NULL,
                round_id TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_scores_score ON scores(score DESC)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_scores_visitor ON scores(visitor_key)")


def get_player_nick(visitor_key: str) -> str | None:
    with sqlite3.connect(DB_PATH, timeout=30) as conn:
        row = conn.execute(
            "SELECT nick FROM players WHERE visitor_key = ?",
            (visitor_key,),
        ).fetchone()
    return row[0] if row else None


def save_player_nick(visitor_key: str, nick: str) -> None:
    stamp = now_iso()
    with sqlite3.connect(DB_PATH, timeout=30) as conn:
        conn.execute(
            """
            INSERT INTO players(visitor_key, nick, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(visitor_key) DO UPDATE SET
                nick = excluded.nick,
                updated_at = excluded.updated_at
            """,
            (visitor_key, nick, stamp, stamp),
        )


def save_score(visitor_key: str, nick: str, score: int, round_id: str) -> bool:
    if not isinstance(score, int):
        return False
    if score < 0 or score > 999_999:
        return False
    if not round_id or len(round_id) > 80:
        return False

    with sqlite3.connect(DB_PATH, timeout=30) as conn:
        try:
            conn.execute(
                """
                INSERT INTO scores(visitor_key, nick, score, round_id, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (visitor_key, nick, score, round_id, now_iso()),
            )
            return True
        except sqlite3.IntegrityError:
            return False


def leaderboard(limit: int = 10) -> list[dict[str, Any]]:
    with sqlite3.connect(DB_PATH, timeout=30) as conn:
        rows = conn.execute(
            """
            SELECT
                nick,
                MAX(score) AS best_score,
                COUNT(*) AS games_played,
                MAX(created_at) AS last_played
            FROM scores
            GROUP BY visitor_key, nick
            ORDER BY best_score DESC, last_played ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return [
        {
            "place": idx + 1,
            "nick": row[0],
            "score": int(row[1]),
            "games": int(row[2]),
            "last_played": row[3],
        }
        for idx, row in enumerate(rows)
    ]


def get_my_best(visitor_key: str) -> int:
    with sqlite3.connect(DB_PATH, timeout=30) as conn:
        row = conn.execute(
            "SELECT MAX(score) FROM scores WHERE visitor_key = ?",
            (visitor_key,),
        ).fetchone()
    return int(row[0] or 0)


def render_css() -> None:
    st.markdown(
        """
        <style>
          .block-container {
            padding-top: 0.6rem;
            padding-bottom: 1rem;
            max-width: 1500px;
          }
          header, footer {
            visibility: hidden;
          }
          [data-testid="stMetric"] {
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(255,255,255,0.08);
            padding: 12px;
            border-radius: 14px;
          }
        </style>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    render_css()
    init_db()

    visitor_key, has_ip = get_visitor_key()
    nick = get_player_nick(visitor_key)

    st.title("🪖 Saperka vs Kurierzy")

    if nick is None:
        st.info("Pierwsze wejście z tego IP. Podaj nick — potem wyniki będą zapisywane w rankingu.")
        if not has_ip:
            st.warning(
                "Nie udało się odczytać IP w tym środowisku, więc aplikacja użyje tymczasowego ID sesji. "
                "Na Streamlit Cloud zwykle działa to lepiej niż lokalnie."
            )

        with st.form("nick_form", clear_on_submit=False):
            raw_nick = st.text_input("Nick", max_chars=24, placeholder="np. Michał")
            accepted = st.checkbox(
                "Rozumiem, że aplikacja zapisze nick, wynik, datę i hash mojego IP.",
                value=False,
            )
            submit = st.form_submit_button("Wejdź do gry")

        if submit:
            cleaned = clean_nick(raw_nick)
            if len(cleaned) < 3:
                st.error("Nick musi mieć minimum 3 znaki.")
            elif not accepted:
                st.error("Zaznacz zgodę na zapis wyniku w rankingu.")
            else:
                save_player_nick(visitor_key, cleaned)
                st.rerun()

        st.stop()

    top = leaderboard(10)
    my_best = get_my_best(visitor_key)

    col1, col2, col3 = st.columns(3)
    col1.metric("Twój nick", nick)
    col2.metric("Twój rekord", my_best)
    col3.metric("Graczy w topce", len(top))

    with st.expander("Zmień nick przypisany do tego IP"):
        with st.form("change_nick_form", clear_on_submit=False):
            new_raw = st.text_input("Nowy nick", value=nick, max_chars=24)
            change = st.form_submit_button("Zapisz nowy nick")
        if change:
            new_nick = clean_nick(new_raw)
            if len(new_nick) < 3:
                st.error("Nick musi mieć minimum 3 znaki.")
            else:
                save_player_nick(visitor_key, new_nick)
                st.success("Nick zmieniony.")
                st.rerun()

    result = _game_component(
        nick=nick,
        leaderboard=top,
        my_best=my_best,
        default=None,
        key="saperka_canvas_game",
    )

    if isinstance(result, dict) and result.get("event") == "score":
        try:
            score = int(result.get("score", 0))
        except Exception:
            score = 0

        round_id = str(result.get("round_id", ""))[:80]
        saved = save_score(visitor_key, nick, score, round_id)

        if saved:
            st.toast(f"Zapisano wynik: {score} pkt")
            st.rerun()

    st.caption(
        "Ranking zapisuje nick, wynik, datę i hash IP, nie surowy adres IP. "
        "Uwaga: lokalna baza SQLite jest dobra do testów i prostego hostingu; na darmowym Streamlit Cloud "
        "dane mogą zniknąć po restarcie lub redeployu. Do produkcji najlepiej podłączyć Supabase, Neon, "
        "Postgres albo Google Sheets."
    )


if __name__ == "__main__":
    main()
