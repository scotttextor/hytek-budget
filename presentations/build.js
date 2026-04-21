// HYTEK Operations Platform — Manager Meeting Presentation v2
// Self-running premium showcase, 4-min loop
// Brand: Black #0B0809 + HYTEK Yellow #FFCB05, Bahnschrift typography

const pptxgen = require("pptxgenjs");
const sharp = require("sharp");

// ---------- PALETTE ----------
const INK           = "0B0809";   // primary dark
const INK_PANEL     = "16100F";   // panel dark
const INK_ELEVATED  = "1F1817";   // elevated card
const INK_HAIR      = "2A2322";   // hairline divider
const PAPER         = "F5F2EE";   // off-white primary
const PAPER_MUTED   = "A8A09E";   // secondary text
const PAPER_FAINT   = "56504E";   // tertiary text
const ACCENT        = "FFCB05";   // HYTEK yellow
const ACCENT_SOFT   = "FFE066";   // lighter tint
const OK            = "6FA36F";
const WARN          = "E8B86A";
const BAD           = "C87069";
const INFO          = "6B8DC4";

// ---------- TYPOGRAPHY ----------
const DISPLAY = "Bahnschrift Condensed";      // heavy condensed display
const DISPLAY_LIGHT = "Bahnschrift Light Condensed";
const BODY = "Calibri";
const BODY_LIGHT = "Calibri Light";
const MONO = "Consolas";

// ---------- DIMENSIONS (16:9 — 10" × 5.625") ----------
const W = 10, H = 5.625;
const M = 0.6; // standard margin

// ---------- SHADOW FACTORIES (pptxgenjs mutates, need fresh each call) ----------
const shadowCard = () => ({ type: "outer", color: "000000", blur: 22, offset: 6, angle: 135, opacity: 0.45 });
const shadowPhone = () => ({ type: "outer", color: "000000", blur: 35, offset: 12, angle: 135, opacity: 0.55 });
const shadowSoft = () => ({ type: "outer", color: "000000", blur: 14, offset: 3, angle: 135, opacity: 0.3 });
const shadowType = () => ({ type: "outer", color: "000000", blur: 18, offset: 4, angle: 135, opacity: 0.4 });

// ---------- BACKGROUND IMAGE GENERATION ----------
async function makeRadialBg(colorCenter, colorEdge, cx = 50, cy = 45, r = 75) {
  const svg = `<svg width="1920" height="1080" xmlns="http://www.w3.org/2000/svg">
    <defs>
      <radialGradient id="g" cx="${cx}%" cy="${cy}%" r="${r}%">
        <stop offset="0%" stop-color="#${colorCenter}"/>
        <stop offset="100%" stop-color="#${colorEdge}"/>
      </radialGradient>
    </defs>
    <rect width="100%" height="100%" fill="url(#g)"/>
  </svg>`;
  const buf = await sharp(Buffer.from(svg)).png({ compressionLevel: 9 }).toBuffer();
  return "image/png;base64," + buf.toString("base64");
}

async function makeLinearBg(color1, color2) {
  const svg = `<svg width="1920" height="1080" xmlns="http://www.w3.org/2000/svg">
    <defs>
      <linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stop-color="#${color1}"/>
        <stop offset="100%" stop-color="#${color2}"/>
      </linearGradient>
    </defs>
    <rect width="100%" height="100%" fill="url(#g)"/>
  </svg>`;
  const buf = await sharp(Buffer.from(svg)).png({ compressionLevel: 9 }).toBuffer();
  return "image/png;base64," + buf.toString("base64");
}

async function main() {
  const BG_CONTENT = await makeRadialBg("211A19", "050404", 50, 40, 80);
  const BG_HERO    = await makeRadialBg("2B2321", "030202", 30, 30, 90);
  const BG_ACCENT  = await makeRadialBg("FFD93D", "E0AC00", 30, 30, 95);

  const pres = new pptxgen();
  pres.layout = "LAYOUT_16x9";
  pres.title = "HYTEK Operations Platform 2026";
  pres.author = "Scott Textor";
  pres.company = "HYTEK Framing";

  // ---------- REUSABLE SLIDE FURNITURE ----------

  function addOverline(slide, number, label) {
    // Thin yellow hairline rule
    slide.addShape(pres.shapes.RECTANGLE, {
      x: M, y: 0.48, w: 0.35, h: 0.025,
      fill: { color: ACCENT }, line: { type: "none" }
    });
    // Small mono kicker text
    slide.addText(`${number}  —  ${label}`, {
      x: M + 0.48, y: 0.38, w: 4, h: 0.25,
      fontFace: MONO, fontSize: 9, color: PAPER_MUTED,
      align: "left", valign: "middle", charSpacing: 6, margin: 0
    });
  }

  function addPageCounter(slide, current) {
    slide.addText(`${String(current).padStart(2, "0")} / 16`, {
      x: W - 1.2, y: H - 0.4, w: 0.9, h: 0.2,
      fontFace: MONO, fontSize: 8, color: PAPER_FAINT,
      align: "right", valign: "middle", charSpacing: 4, margin: 0
    });
  }

  // ---------- SLIDE 1 · TITLE ----------
  {
    const s = pres.addSlide();
    s.background = { data: BG_HERO };

    // Tiny overline
    s.addShape(pres.shapes.RECTANGLE, {
      x: M, y: 0.65, w: 0.5, h: 0.025,
      fill: { color: ACCENT }, line: { type: "none" }
    });
    s.addText("HYTEK FRAMING  ·  APRIL 2026", {
      x: M + 0.65, y: 0.55, w: 5, h: 0.25,
      fontFace: MONO, fontSize: 10, color: PAPER_MUTED,
      align: "left", valign: "middle", charSpacing: 8, margin: 0
    });

    // Massive wordmark with shadow
    s.addText("HYTEK", {
      x: M, y: 1.35, w: 8.8, h: 2.3,
      fontFace: DISPLAY, fontSize: 240, color: ACCENT,
      align: "left", valign: "middle", charSpacing: 16, margin: 0, bold: true,
      shadow: shadowType()
    });

    // Thin full-width hairline under wordmark
    s.addShape(pres.shapes.RECTANGLE, {
      x: M, y: 3.85, w: W - 2 * M, h: 0.01,
      fill: { color: "3A3230" }, line: { type: "none" }
    });

    // Tagline
    s.addText("OPERATIONS PLATFORM", {
      x: M, y: 4.05, w: 8.8, h: 0.5,
      fontFace: DISPLAY, fontSize: 30, color: PAPER,
      align: "left", valign: "middle", charSpacing: 14, margin: 0
    });
    s.addText("A quiet revolution in how we run jobs.", {
      x: M, y: 4.55, w: 8.8, h: 0.4,
      fontFace: BODY_LIGHT, fontSize: 13, color: PAPER_MUTED,
      align: "left", valign: "middle", italic: true, margin: 0
    });

    s.addText("01 / 16", {
      x: W - 1.2, y: H - 0.4, w: 0.9, h: 0.2,
      fontFace: MONO, fontSize: 8, color: PAPER_FAINT,
      align: "right", valign: "middle", charSpacing: 4, margin: 0
    });
  }

  // ---------- SLIDE 2 · BEFORE ----------
  {
    const s = pres.addSlide();
    s.background = { data: BG_CONTENT };
    addOverline(s, "02", "BEFORE");

    s.addText("Five departments.", {
      x: M, y: 1.6, w: W - 2 * M, h: 1.1,
      fontFace: DISPLAY, fontSize: 90, color: PAPER,
      align: "left", valign: "middle", charSpacing: 2, margin: 0
    });
    s.addText("Zero shared data.", {
      x: M, y: 2.65, w: W - 2 * M, h: 1.1,
      fontFace: DISPLAY, fontSize: 90, color: ACCENT,
      align: "left", valign: "middle", charSpacing: 2, margin: 0
    });

    // Short yellow accent line
    s.addShape(pres.shapes.RECTANGLE, {
      x: M, y: 4.05, w: 0.8, h: 0.035,
      fill: { color: ACCENT }, line: { type: "none" }
    });
    s.addText("Paper claims. Lost variations. Nobody knew where a job really stood.", {
      x: M, y: 4.2, w: 8, h: 0.5,
      fontFace: BODY_LIGHT, fontSize: 15, color: PAPER_MUTED,
      align: "left", valign: "middle", italic: true, margin: 0
    });

    addPageCounter(s, 2);
  }

  // ---------- SLIDE 3 · NOW (the solution) ----------
  {
    const s = pres.addSlide();
    s.background = { data: BG_CONTENT };
    addOverline(s, "03", "NOW");

    s.addText("One platform.", {
      x: M, y: 1.1, w: W - 2 * M, h: 1.0,
      fontFace: DISPLAY, fontSize: 76, color: PAPER,
      align: "left", valign: "middle", charSpacing: 2, margin: 0
    });
    s.addText("Five apps. One database.", {
      x: M, y: 2.0, w: W - 2 * M, h: 0.7,
      fontFace: DISPLAY, fontSize: 36, color: ACCENT,
      align: "left", valign: "middle", charSpacing: 6, margin: 0
    });

    // Elegant app flow strip
    const apps = ["PLANNER", "HUB", "DETAILING", "DISPATCH", "INSTALL"];
    const tileW = 1.55, tileH = 0.95, gap = 0.18;
    const totalW = apps.length * tileW + (apps.length - 1) * gap;
    const startX = (W - totalW) / 2;
    const tileY = 3.25;

    apps.forEach((app, i) => {
      const x = startX + i * (tileW + gap);
      s.addShape(pres.shapes.RECTANGLE, {
        x, y: tileY, w: tileW, h: tileH,
        fill: { color: INK_ELEVATED }, line: { color: "3A3230", width: 0.5 },
        shadow: shadowCard()
      });
      // Thin top accent
      s.addShape(pres.shapes.RECTANGLE, {
        x, y: tileY, w: tileW, h: 0.04,
        fill: { color: ACCENT }, line: { type: "none" }
      });
      s.addText(app, {
        x, y: tileY, w: tileW, h: tileH,
        fontFace: DISPLAY, fontSize: 15, color: PAPER,
        align: "center", valign: "middle", charSpacing: 4, margin: 0
      });
    });

    // Thin horizontal line connecting tiles conceptually
    s.addShape(pres.shapes.RECTANGLE, {
      x: M, y: 4.45, w: W - 2 * M, h: 0.005,
      fill: { color: "3A3230" }, line: { type: "none" }
    });
    s.addText("SHARED DATABASE  ·  INVOICING FEEDS LIVE FROM THE SAME SOURCE", {
      x: M, y: 4.6, w: W - 2 * M, h: 0.3,
      fontFace: MONO, fontSize: 8, color: PAPER_FAINT,
      align: "center", valign: "middle", charSpacing: 4, margin: 0
    });

    addPageCounter(s, 3);
  }

  // ---------- SLIDE 4 · SECTION BREAK · THE APPS ----------
  {
    const s = pres.addSlide();
    s.background = { data: BG_ACCENT };

    // Top overline in black
    s.addShape(pres.shapes.RECTANGLE, {
      x: M, y: 0.65, w: 0.4, h: 0.03,
      fill: { color: INK }, line: { type: "none" }
    });
    s.addText("PART ONE", {
      x: M + 0.55, y: 0.55, w: 4, h: 0.25,
      fontFace: MONO, fontSize: 10, color: INK,
      align: "left", valign: "middle", charSpacing: 10, margin: 0
    });

    // Giant text centered
    s.addText("The apps.", {
      x: M, y: 1.9, w: W - 2 * M, h: 2.2,
      fontFace: DISPLAY, fontSize: 140, color: INK,
      align: "left", valign: "middle", charSpacing: 4, margin: 0, bold: true
    });

    // Bottom caption
    s.addText("Five products. One operating system for the company.", {
      x: M, y: 4.5, w: W - 2 * M, h: 0.4,
      fontFace: BODY_LIGHT, fontSize: 14, color: INK,
      align: "left", valign: "middle", italic: true, margin: 0
    });

    s.addText("04 / 16", {
      x: W - 1.2, y: H - 0.4, w: 0.9, h: 0.2,
      fontFace: MONO, fontSize: 8, color: INK,
      align: "right", valign: "middle", charSpacing: 4, margin: 0
    });
  }

  // ---------- SHARED: SPLIT LAYOUT HELPER (headline left, visual right) ----------
  function addSplitHeader(slide, overline, num, headline, accent, body) {
    addOverline(slide, num, overline);
    slide.addText(headline, {
      x: M, y: 1.1, w: 4.6, h: 1.1,
      fontFace: DISPLAY, fontSize: 56, color: PAPER,
      align: "left", valign: "top", charSpacing: 2, margin: 0
    });
    slide.addText(accent, {
      x: M, y: 2.05, w: 4.6, h: 0.95,
      fontFace: DISPLAY, fontSize: 56, color: ACCENT,
      align: "left", valign: "top", charSpacing: 2, margin: 0
    });
    // Tiny divider
    slide.addShape(pres.shapes.RECTANGLE, {
      x: M, y: 3.2, w: 0.5, h: 0.025,
      fill: { color: ACCENT }, line: { type: "none" }
    });
    slide.addText(body, {
      x: M, y: 3.35, w: 4.6, h: 1.5,
      fontFace: BODY_LIGHT, fontSize: 13, color: PAPER_MUTED,
      align: "left", valign: "top", margin: 0, paraSpaceAfter: 4
    });
  }

  // ---------- SLIDE 5 · HUB ----------
  {
    const s = pres.addSlide();
    s.background = { data: BG_CONTENT };
    addSplitHeader(s, "HUB", "05",
      "One login.",
      "Every app.",
      "Central launcher for every department. One set of credentials. Staff click straight through — no re-logins, no page-hunting."
    );

    // Right: premium 6-tile hub mock
    const tiles = [
      { label: "PLANNER", sub: "Est. & margin" },
      { label: "DETAILING", sub: "Jobs & specs" },
      { label: "DISPATCH", sub: "Trips & loads" },
      { label: "INSTALL", sub: "Site claims" },
      { label: "INVOICING", sub: "Progress claims" },
      { label: "FAB", sub: "Coming soon", muted: true }
    ];
    const gx = 5.55, gy = 1.0, gw = 1.35, gh = 1.3, gp = 0.16;
    tiles.forEach((t, i) => {
      const col = i % 3, row = Math.floor(i / 3);
      const x = gx + col * (gw + gp);
      const y = gy + row * (gh + gp);
      s.addShape(pres.shapes.RECTANGLE, {
        x, y, w: gw, h: gh,
        fill: { color: t.muted ? INK_PANEL : INK_ELEVATED },
        line: { color: t.muted ? "2A2322" : "3A3230", width: 0.5 },
        shadow: t.muted ? undefined : shadowCard()
      });
      // Top accent
      if (!t.muted) {
        s.addShape(pres.shapes.RECTANGLE, {
          x, y, w: gw, h: 0.04, fill: { color: ACCENT }, line: { type: "none" }
        });
      }
      s.addText(t.label, {
        x, y: y + 0.28, w: gw, h: 0.45,
        fontFace: DISPLAY, fontSize: 14,
        color: t.muted ? PAPER_FAINT : PAPER,
        align: "center", valign: "middle", charSpacing: 3, margin: 0
      });
      s.addText(t.sub, {
        x, y: y + 0.78, w: gw, h: 0.3,
        fontFace: MONO, fontSize: 8,
        color: t.muted ? PAPER_FAINT : ACCENT,
        align: "center", valign: "middle", charSpacing: 2, margin: 0
      });
    });

    addPageCounter(s, 5);
  }

  // ---------- SLIDE 6 · DETAILING ----------
  {
    const s = pres.addSlide();
    s.background = { data: BG_CONTENT };
    addSplitHeader(s, "DETAILING", "06",
      "Draw it.",
      "Once.",
      "Every job flows through the detailing pipeline. Status visible to every department — no more chasing detailers on WhatsApp."
    );

    // Right: job pipeline rows with status
    const jobs = [
      { name: "Springfield Tower 4B",   status: "DELIVERED",   color: OK },
      { name: "Park Rd Apartments",     status: "FABRICATING", color: ACCENT },
      { name: "Hospital Block C",       status: "DETAILING",   color: INFO },
      { name: "Chermside Offices",      status: "DETAILING",   color: INFO },
      { name: "Test 30 Unit Complex",   status: "QUOTED",      color: PAPER_FAINT }
    ];
    const listX = 5.4, listY = 1.0, rowH = 0.6, listW = 4.2;
    jobs.forEach((j, i) => {
      const y = listY + i * (rowH + 0.1);
      s.addShape(pres.shapes.RECTANGLE, {
        x: listX, y, w: listW, h: rowH,
        fill: { color: INK_ELEVATED }, line: { color: "2A2322", width: 0.5 },
        shadow: shadowSoft()
      });
      // Status stripe on left
      s.addShape(pres.shapes.RECTANGLE, {
        x: listX, y, w: 0.06, h: rowH,
        fill: { color: j.color }, line: { type: "none" }
      });
      s.addText(j.name, {
        x: listX + 0.28, y, w: 2.2, h: rowH,
        fontFace: BODY, fontSize: 11, color: PAPER,
        align: "left", valign: "middle", margin: 0, bold: true
      });
      s.addText(j.status, {
        x: listX + 2.5, y, w: listW - 2.6, h: rowH,
        fontFace: MONO, fontSize: 9, color: j.color,
        align: "right", valign: "middle", charSpacing: 3, margin: 0, bold: true
      });
    });

    addPageCounter(s, 6);
  }

  // ---------- SLIDE 7 · DISPATCH ----------
  {
    const s = pres.addSlide();
    s.background = { data: BG_CONTENT };
    addSplitHeader(s, "DISPATCH", "07",
      "Logistics.",
      "Live board.",
      "Every truck, every trip, every delivery. Drivers tick off loads on their phone. Installers know exactly what's landing when."
    );

    // Right: schedule board with subtle styling
    const days = ["MON", "TUE", "WED", "THU", "FRI"];
    const trucks = ["TRUCK 1", "TRUCK 2", "TRUCK 3"];
    const schedule = [
      [null, "BOOKED", "BOOKED", null, "BOOKED"],
      ["BOOKED", "BOOKED", "URGENT", null, "BOOKED"],
      ["BOOKED", null, "BOOKED", "BOOKED", null]
    ];

    const boardX = 5.5, boardY = 1.0, cellW = 0.78, cellH = 0.62, labelW = 0.72;
    // Header day labels
    days.forEach((d, i) => {
      s.addText(d, {
        x: boardX + labelW + i * cellW, y: boardY, w: cellW, h: 0.35,
        fontFace: MONO, fontSize: 9, color: ACCENT,
        align: "center", valign: "middle", charSpacing: 3, margin: 0
      });
    });
    trucks.forEach((t, r) => {
      const y = boardY + 0.4 + r * (cellH + 0.1);
      s.addText(t, {
        x: boardX, y, w: labelW, h: cellH,
        fontFace: MONO, fontSize: 8, color: PAPER_MUTED,
        align: "left", valign: "middle", charSpacing: 2, margin: 0
      });
      days.forEach((_, c) => {
        const x = boardX + labelW + c * cellW;
        const slot = schedule[r][c];
        const isUrgent = slot === "URGENT";
        const isEmpty = slot === null;
        s.addShape(pres.shapes.RECTANGLE, {
          x: x + 0.03, y, w: cellW - 0.1, h: cellH,
          fill: { color: isUrgent ? ACCENT : (isEmpty ? INK_PANEL : INK_ELEVATED) },
          line: { type: "none" },
          shadow: isEmpty ? undefined : (isUrgent ? shadowSoft() : shadowSoft())
        });
        if (!isEmpty) {
          s.addText(slot, {
            x: x + 0.03, y, w: cellW - 0.1, h: cellH,
            fontFace: MONO, fontSize: 8,
            color: isUrgent ? INK : PAPER_MUTED,
            align: "center", valign: "middle", charSpacing: 2, margin: 0, bold: isUrgent
          });
        }
      });
    });

    addPageCounter(s, 7);
  }

  // ---------- SLIDE 8 · INSTALL OFFICE ----------
  {
    const s = pres.addSlide();
    s.background = { data: BG_CONTENT };
    addSplitHeader(s, "INSTALL · OFFICE", "08",
      "Budget.",
      "Live. Per job.",
      "Every dollar of install cost tracked against quote. Site claims flow in, numbers update instantly. No more end-of-month surprises."
    );

    // Right: premium budget panel
    const rows = [
      { code: "INSTALL",    budget: "$48,500", spent: "$31,200", pct: 64 },
      { code: "CRANAGE",    budget: "$12,000", spent: "$8,750",  pct: 73 },
      { code: "REWORK",     budget: "$2,500",  spent: "$1,100",  pct: 44 },
      { code: "VARIATIONS", budget: "$6,000",  spent: "$5,400",  pct: 90 }
    ];
    const tX = 5.4, tY = 1.0, tW = 4.2;
    // Panel wrapper
    s.addShape(pres.shapes.RECTANGLE, {
      x: tX, y: tY, w: tW, h: 3.7,
      fill: { color: INK_ELEVATED }, line: { color: "2A2322", width: 0.5 },
      shadow: shadowCard()
    });
    // Header row
    s.addText("ITEM", { x: tX + 0.2, y: tY + 0.15, w: 1.3, h: 0.3, fontFace: MONO, fontSize: 8, color: PAPER_MUTED, align: "left", valign: "middle", charSpacing: 3, margin: 0 });
    s.addText("BUDGET", { x: tX + 1.5, y: tY + 0.15, w: 1.0, h: 0.3, fontFace: MONO, fontSize: 8, color: PAPER_MUTED, align: "right", valign: "middle", charSpacing: 3, margin: 0 });
    s.addText("SPENT", { x: tX + 2.5, y: tY + 0.15, w: 1.0, h: 0.3, fontFace: MONO, fontSize: 8, color: PAPER_MUTED, align: "right", valign: "middle", charSpacing: 3, margin: 0 });
    s.addText("USED", { x: tX + 3.5, y: tY + 0.15, w: 0.6, h: 0.3, fontFace: MONO, fontSize: 8, color: PAPER_MUTED, align: "right", valign: "middle", charSpacing: 3, margin: 0 });
    // Divider
    s.addShape(pres.shapes.RECTANGLE, { x: tX + 0.2, y: tY + 0.5, w: tW - 0.4, h: 0.01, fill: { color: INK_HAIR }, line: { type: "none" } });
    rows.forEach((r, i) => {
      const y = tY + 0.65 + i * 0.72;
      s.addText(r.code, { x: tX + 0.2, y, w: 1.3, h: 0.35, fontFace: BODY, fontSize: 12, color: PAPER, align: "left", valign: "middle", bold: true, margin: 0 });
      s.addText(r.budget, { x: tX + 1.5, y, w: 1.0, h: 0.35, fontFace: BODY_LIGHT, fontSize: 11, color: PAPER_MUTED, align: "right", valign: "middle", margin: 0 });
      s.addText(r.spent, { x: tX + 2.5, y, w: 1.0, h: 0.35, fontFace: BODY, fontSize: 11, color: PAPER, align: "right", valign: "middle", bold: true, margin: 0 });
      // Usage bar
      const barW = 3.6, barX = tX + 0.2;
      s.addShape(pres.shapes.RECTANGLE, { x: barX, y: y + 0.42, w: barW, h: 0.08, fill: { color: INK_HAIR }, line: { type: "none" } });
      const fillColor = r.pct >= 85 ? BAD : (r.pct >= 70 ? WARN : OK);
      s.addShape(pres.shapes.RECTANGLE, { x: barX, y: y + 0.42, w: barW * (r.pct / 100), h: 0.08, fill: { color: fillColor }, line: { type: "none" } });
      s.addText(r.pct + "%", { x: tX + 3.5, y, w: 0.6, h: 0.35, fontFace: MONO, fontSize: 10, color: fillColor, align: "right", valign: "middle", margin: 0, bold: true });
    });

    addPageCounter(s, 8);
  }

  // ---------- SLIDE 9 · INSTALL MOBILE (two phones) ----------
  {
    const s = pres.addSlide();
    s.background = { data: BG_CONTENT };
    addOverline(s, "09", "INSTALL · MOBILE");

    s.addText("Two taps.", {
      x: M, y: 1.05, w: 4.8, h: 1.0,
      fontFace: DISPLAY, fontSize: 60, color: PAPER,
      align: "left", valign: "top", charSpacing: 2, margin: 0
    });
    s.addText("Fifteen seconds.", {
      x: M, y: 1.85, w: 4.8, h: 1.0,
      fontFace: DISPLAY, fontSize: 60, color: ACCENT,
      align: "left", valign: "top", charSpacing: 2, margin: 0
    });

    // Sub caption
    s.addShape(pres.shapes.RECTANGLE, { x: M, y: 3.3, w: 0.5, h: 0.025, fill: { color: ACCENT }, line: { type: "none" } });
    s.addText("PIN login. Works on 4G in a roof cavity. Works offline. Syncs when signal returns.", {
      x: M, y: 3.45, w: 5, h: 1.0,
      fontFace: BODY_LIGHT, fontSize: 13, color: PAPER_MUTED,
      align: "left", valign: "top", margin: 0
    });

    // Right: two phone mockups side-by-side
    function drawPhone(phX, phY, phW, phH, drawScreen) {
      // Outer shell
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
        x: phX, y: phY, w: phW, h: phH,
        fill: { color: "050404" }, line: { color: "2A2322", width: 0.75 }, rectRadius: 0.22,
        shadow: shadowPhone()
      });
      // Screen
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
        x: phX + 0.1, y: phY + 0.22, w: phW - 0.2, h: phH - 0.44,
        fill: { color: INK }, line: { type: "none" }, rectRadius: 0.14
      });
      // Notch
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
        x: phX + phW / 2 - 0.4, y: phY + 0.06, w: 0.8, h: 0.14,
        fill: { color: "050404" }, line: { type: "none" }, rectRadius: 0.05
      });
      drawScreen(phX + 0.1, phY + 0.22, phW - 0.2, phH - 0.44);
    }

    // Phone 1 — PIN
    const p1X = 5.6, p1Y = 1.0, p1W = 2.0, p1H = 4.0;
    drawPhone(p1X, p1Y, p1W, p1H, (sx, sy, sw, sh) => {
      // brand
      s.addText("HYTEK", { x: sx, y: sy + 0.2, w: sw, h: 0.25, fontFace: DISPLAY, fontSize: 14, color: ACCENT, align: "center", valign: "middle", charSpacing: 4, margin: 0 });
      s.addText("ENTER PIN", { x: sx, y: sy + 0.5, w: sw, h: 0.2, fontFace: MONO, fontSize: 7, color: PAPER_MUTED, align: "center", valign: "middle", charSpacing: 4, margin: 0 });
      // dots
      for (let i = 0; i < 4; i++) {
        s.addShape(pres.shapes.OVAL, {
          x: sx + sw / 2 - 0.4 + i * 0.23, y: sy + 0.85, w: 0.13, h: 0.13,
          fill: { color: i < 2 ? ACCENT : INK_ELEVATED }, line: { type: "none" }
        });
      }
      // keypad
      const keys = ["1","2","3","4","5","6","7","8","9","","0","⌫"];
      const keyW = 0.38, keyH = 0.38, keyGap = 0.08;
      const padX = sx + sw / 2 - (3 * keyW + 2 * keyGap) / 2;
      const padY = sy + 1.2;
      keys.forEach((k, i) => {
        const col = i % 3, row = Math.floor(i / 3);
        if (k === "") return;
        const kx = padX + col * (keyW + keyGap);
        const ky = padY + row * (keyH + keyGap);
        s.addShape(pres.shapes.OVAL, {
          x: kx, y: ky, w: keyW, h: keyH,
          fill: { color: INK_ELEVATED }, line: { color: "2A2322", width: 0.5 }
        });
        s.addText(k, {
          x: kx, y: ky, w: keyW, h: keyH,
          fontFace: BODY, fontSize: 13, color: PAPER,
          align: "center", valign: "middle", margin: 0
        });
      });
    });

    // Phone 2 — Claim form
    const p2X = 7.85, p2Y = 1.0, p2W = 2.0, p2H = 4.0;
    drawPhone(p2X, p2Y, p2W, p2H, (sx, sy, sw, sh) => {
      // Job header
      s.addShape(pres.shapes.RECTANGLE, { x: sx, y: sy + 0.1, w: sw, h: 0.4, fill: { color: ACCENT }, line: { type: "none" } });
      s.addText("SPRINGFIELD 4B", { x: sx, y: sy + 0.1, w: sw, h: 0.4, fontFace: DISPLAY, fontSize: 10, color: INK, align: "center", valign: "middle", charSpacing: 3, margin: 0 });
      // Label
      s.addText("PROGRESS CLAIM", { x: sx + 0.1, y: sy + 0.6, w: sw - 0.2, h: 0.2, fontFace: MONO, fontSize: 7, color: PAPER_MUTED, align: "left", valign: "middle", charSpacing: 3, margin: 0 });
      // Item field
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: sx + 0.1, y: sy + 0.82, w: sw - 0.2, h: 0.38, fill: { color: INK_ELEVATED }, line: { color: ACCENT, width: 0.5 }, rectRadius: 0.05 });
      s.addText("Install — Type A", { x: sx + 0.2, y: sy + 0.82, w: sw - 0.3, h: 0.38, fontFace: BODY, fontSize: 9, color: PAPER, align: "left", valign: "middle", margin: 0 });
      // Amount label
      s.addText("AMOUNT", { x: sx + 0.1, y: sy + 1.35, w: sw - 0.2, h: 0.2, fontFace: MONO, fontSize: 7, color: PAPER_MUTED, align: "left", valign: "middle", charSpacing: 3, margin: 0 });
      // Amount field
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: sx + 0.1, y: sy + 1.57, w: sw - 0.2, h: 0.5, fill: { color: INK }, line: { color: ACCENT, width: 1 }, rectRadius: 0.04 });
      s.addText("$ 3,450", { x: sx + 0.2, y: sy + 1.57, w: sw - 0.3, h: 0.5, fontFace: DISPLAY, fontSize: 18, color: ACCENT, align: "left", valign: "middle", charSpacing: 2, margin: 0 });
      // Hint
      s.addText("78% of item budget", { x: sx + 0.1, y: sy + 2.15, w: sw - 0.2, h: 0.2, fontFace: MONO, fontSize: 7, color: WARN, align: "left", valign: "middle", margin: 0 });
      // Button
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: sx + 0.1, y: sy + 2.65, w: sw - 0.2, h: 0.45, fill: { color: ACCENT }, line: { type: "none" }, rectRadius: 0.07, shadow: shadowSoft() });
      s.addText("LOG CLAIM", { x: sx + 0.1, y: sy + 2.65, w: sw - 0.2, h: 0.45, fontFace: DISPLAY, fontSize: 12, color: INK, align: "center", valign: "middle", charSpacing: 4, margin: 0 });
    });

    addPageCounter(s, 9);
  }

  // ---------- SLIDE 10 · SECTION BREAK · HOW IT FLOWS ----------
  {
    const s = pres.addSlide();
    s.background = { data: BG_ACCENT };

    s.addShape(pres.shapes.RECTANGLE, { x: M, y: 0.65, w: 0.4, h: 0.03, fill: { color: INK }, line: { type: "none" } });
    s.addText("PART TWO", {
      x: M + 0.55, y: 0.55, w: 4, h: 0.25,
      fontFace: MONO, fontSize: 10, color: INK,
      align: "left", valign: "middle", charSpacing: 10, margin: 0
    });

    s.addText("The flow.", {
      x: M, y: 1.9, w: W - 2 * M, h: 2.2,
      fontFace: DISPLAY, fontSize: 140, color: INK,
      align: "left", valign: "middle", charSpacing: 4, margin: 0, bold: true
    });

    s.addText("From a tap on site to a line on an invoice. Nothing lost in between.", {
      x: M, y: 4.5, w: W - 2 * M, h: 0.4,
      fontFace: BODY_LIGHT, fontSize: 14, color: INK,
      align: "left", valign: "middle", italic: true, margin: 0
    });

    s.addText("10 / 16", {
      x: W - 1.2, y: H - 0.4, w: 0.9, h: 0.2,
      fontFace: MONO, fontSize: 8, color: INK,
      align: "right", valign: "middle", charSpacing: 4, margin: 0
    });
  }

  // ---------- SLIDE 11 · VARIATIONS ----------
  {
    const s = pres.addSlide();
    s.background = { data: BG_CONTENT };
    addOverline(s, "11", "VARIATIONS");

    s.addText("Every change.", {
      x: M, y: 0.95, w: W - 2 * M, h: 1.0,
      fontFace: DISPLAY, fontSize: 68, color: PAPER,
      align: "left", valign: "middle", charSpacing: 2, margin: 0
    });
    s.addText("Tracked.", {
      x: M, y: 1.85, w: W - 2 * M, h: 1.0,
      fontFace: DISPLAY, fontSize: 68, color: ACCENT,
      align: "left", valign: "middle", charSpacing: 2, margin: 0
    });

    // Premium state machine
    const states = ["RAISED", "PRICED", "SUBMITTED", "APPROVED", "INVOICED"];
    const sW = 1.5, sH = 0.85, sGap = 0.18;
    const sTotalW = states.length * sW + (states.length - 1) * sGap;
    const sStartX = (W - sTotalW) / 2;
    const sY = 3.35;

    states.forEach((st, i) => {
      const x = sStartX + i * (sW + sGap);
      const isLast = i === states.length - 1;
      s.addShape(pres.shapes.RECTANGLE, {
        x, y: sY, w: sW, h: sH,
        fill: { color: isLast ? ACCENT : INK_ELEVATED },
        line: { color: isLast ? ACCENT : "3A3230", width: 0.5 },
        shadow: shadowCard()
      });
      if (!isLast) {
        s.addShape(pres.shapes.RECTANGLE, {
          x, y: sY, w: sW, h: 0.04, fill: { color: ACCENT }, line: { type: "none" }
        });
      }
      s.addText(st, {
        x, y: sY, w: sW, h: sH,
        fontFace: DISPLAY, fontSize: 14,
        color: isLast ? INK : PAPER,
        align: "center", valign: "middle", charSpacing: 4, margin: 0
      });
      // Step number
      s.addText(`0${i + 1}`, {
        x, y: sY + sH + 0.1, w: sW, h: 0.2,
        fontFace: MONO, fontSize: 8, color: PAPER_FAINT,
        align: "center", valign: "middle", charSpacing: 3, margin: 0
      });
      // Tiny arrow between cards (hairline, not triangle)
      if (i < states.length - 1) {
        const arrowX = x + sW + 0.02;
        const arrowY = sY + sH / 2;
        s.addShape(pres.shapes.RECTANGLE, {
          x: arrowX, y: arrowY - 0.01, w: 0.14, h: 0.02,
          fill: { color: ACCENT }, line: { type: "none" }
        });
      }
    });

    s.addShape(pres.shapes.RECTANGLE, { x: M, y: 4.7, w: 0.5, h: 0.025, fill: { color: ACCENT }, line: { type: "none" } });
    s.addText("PO-backed. Audit trail. Nothing slips between site and invoicing.", {
      x: M, y: 4.85, w: W - 2 * M, h: 0.4,
      fontFace: BODY_LIGHT, fontSize: 12, color: PAPER_MUTED,
      align: "left", valign: "middle", italic: true, margin: 0
    });

    addPageCounter(s, 11);
  }

  // ---------- SLIDE 12 · REWORK ----------
  {
    const s = pres.addSlide();
    s.background = { data: BG_CONTENT };
    addOverline(s, "12", "REWORK");

    s.addText("Every defect.", {
      x: M, y: 0.95, w: W - 2 * M, h: 1.0,
      fontFace: DISPLAY, fontSize: 68, color: PAPER,
      align: "left", valign: "middle", charSpacing: 2, margin: 0
    });
    s.addText("Owned.", {
      x: M, y: 1.85, w: W - 2 * M, h: 1.0,
      fontFace: DISPLAY, fontSize: 68, color: ACCENT,
      align: "left", valign: "middle", charSpacing: 2, margin: 0
    });

    // 3 columns
    const payers = [
      { who: "FABRICATION", note: "Back-charged\nto the fab line" },
      { who: "INSTALLER",   note: "Back-charged\nto the crew" },
      { who: "HYTEK",       note: "Absorbed\nand investigated" }
    ];
    const pW = 2.7, pH = 1.5, pGap = 0.25;
    const pTotalW = payers.length * pW + (payers.length - 1) * pGap;
    const pStartX = (W - pTotalW) / 2;
    const pY = 3.25;

    payers.forEach((p, i) => {
      const x = pStartX + i * (pW + pGap);
      s.addShape(pres.shapes.RECTANGLE, { x, y: pY, w: pW, h: pH, fill: { color: INK_ELEVATED }, line: { color: "3A3230", width: 0.5 }, shadow: shadowCard() });
      s.addShape(pres.shapes.RECTANGLE, { x, y: pY, w: pW, h: 0.04, fill: { color: ACCENT }, line: { type: "none" } });
      // Small step number
      s.addText(`0${i + 1}`, { x: x + 0.2, y: pY + 0.2, w: 0.4, h: 0.2, fontFace: MONO, fontSize: 9, color: ACCENT, align: "left", valign: "middle", charSpacing: 2, margin: 0 });
      s.addText(p.who, { x, y: pY + 0.4, w: pW, h: 0.45, fontFace: DISPLAY, fontSize: 20, color: PAPER, align: "center", valign: "middle", charSpacing: 4, margin: 0 });
      s.addText(p.note, { x: x + 0.2, y: pY + 0.95, w: pW - 0.4, h: 0.5, fontFace: BODY_LIGHT, fontSize: 11, color: PAPER_MUTED, align: "center", valign: "top", margin: 0 });
    });

    addPageCounter(s, 12);
  }

  // ---------- SLIDE 13 · INVOICING FLOW (combines Invoicing + Xero) ----------
  {
    const s = pres.addSlide();
    s.background = { data: BG_CONTENT };
    addOverline(s, "13", "INVOICING · XERO");

    s.addText("Site logs", {
      x: M, y: 0.95, w: W - 2 * M, h: 1.0,
      fontFace: DISPLAY, fontSize: 68, color: PAPER,
      align: "left", valign: "middle", charSpacing: 2, margin: 0
    });
    s.addText("become invoices.", {
      x: M, y: 1.85, w: W - 2 * M, h: 1.0,
      fontFace: DISPLAY, fontSize: 68, color: ACCENT,
      align: "left", valign: "middle", charSpacing: 2, margin: 0
    });

    // Flow: 3 nodes + 2 connectors
    const nodeY = 3.25, nodeH = 1.15;
    const n1X = 0.7, n1W = 2.1;
    const n2X = 4.0, n2W = 2.1;
    const n3X = 7.3, n3W = 2.1;

    function drawNode(x, w, label, sub, accent) {
      s.addShape(pres.shapes.RECTANGLE, {
        x, y: nodeY, w, h: nodeH,
        fill: { color: accent ? ACCENT : INK_ELEVATED },
        line: { color: accent ? ACCENT : "3A3230", width: 0.5 },
        shadow: shadowCard()
      });
      if (!accent) {
        s.addShape(pres.shapes.RECTANGLE, { x, y: nodeY, w, h: 0.04, fill: { color: ACCENT }, line: { type: "none" } });
      }
      s.addText(label, { x, y: nodeY + 0.18, w, h: 0.4, fontFace: DISPLAY, fontSize: 14, color: accent ? INK : PAPER, align: "center", valign: "middle", charSpacing: 4, margin: 0 });
      s.addText(sub, { x: x + 0.1, y: nodeY + 0.58, w: w - 0.2, h: 0.45, fontFace: BODY_LIGHT, fontSize: 10, color: accent ? INK : PAPER_MUTED, align: "center", valign: "top", margin: 0 });
    }

    drawNode(n1X, n1W, "SUPERVISOR", "Taps LOG CLAIM\non their phone", false);
    drawNode(n2X, n2W, "PROGRESS CLAIM", "Line item appears\non the job invoice", true);
    drawNode(n3X, n3W, "XERO", "Draft invoice\nauto-created", false);

    // Connectors (hairlines with small dots)
    s.addShape(pres.shapes.RECTANGLE, { x: n1X + n1W, y: nodeY + nodeH / 2 - 0.01, w: n2X - (n1X + n1W), h: 0.02, fill: { color: ACCENT }, line: { type: "none" } });
    s.addShape(pres.shapes.OVAL, { x: n2X - 0.1, y: nodeY + nodeH / 2 - 0.06, w: 0.12, h: 0.12, fill: { color: ACCENT }, line: { type: "none" } });
    s.addShape(pres.shapes.RECTANGLE, { x: n2X + n2W, y: nodeY + nodeH / 2 - 0.01, w: n3X - (n2X + n2W), h: 0.02, fill: { color: ACCENT }, line: { type: "none" } });
    s.addShape(pres.shapes.OVAL, { x: n3X - 0.1, y: nodeY + nodeH / 2 - 0.06, w: 0.12, h: 0.12, fill: { color: ACCENT }, line: { type: "none" } });

    // Caption
    s.addShape(pres.shapes.RECTANGLE, { x: M, y: 4.7, w: 0.5, h: 0.025, fill: { color: ACCENT }, line: { type: "none" } });
    s.addText("Zero re-typing. Zero missed variations. Accounts reviews drafts, doesn't create them.", {
      x: M, y: 4.85, w: W - 2 * M, h: 0.4,
      fontFace: BODY_LIGHT, fontSize: 12, color: PAPER_MUTED,
      align: "left", valign: "middle", italic: true, margin: 0
    });

    addPageCounter(s, 13);
  }

  // ---------- SLIDE 14 · THE PROOF (hero stat layout) ----------
  {
    const s = pres.addSlide();
    s.background = { data: BG_HERO };
    addOverline(s, "14", "THE PROOF");

    // Primary hero stat (left, giant but contained)
    s.addText("94", {
      x: M, y: 1.0, w: 4.5, h: 2.8,
      fontFace: DISPLAY, fontSize: 280, color: ACCENT,
      align: "left", valign: "middle", charSpacing: 0, margin: 0, bold: true,
      shadow: shadowType()
    });
    // Short hairline under the number
    s.addShape(pres.shapes.RECTANGLE, {
      x: M, y: 3.95, w: 0.6, h: 0.03,
      fill: { color: ACCENT }, line: { type: "none" }
    });
    s.addText("TESTS GREEN", {
      x: M, y: 4.1, w: 4.5, h: 0.4,
      fontFace: DISPLAY, fontSize: 20, color: PAPER,
      align: "left", valign: "middle", charSpacing: 6, margin: 0
    });
    s.addText("Every feature backed by automated proof. Nothing ships without a test.", {
      x: M, y: 4.5, w: 4.5, h: 0.6,
      fontFace: BODY_LIGHT, fontSize: 11, color: PAPER_MUTED,
      align: "left", valign: "top", margin: 0, italic: true
    });

    // Right column — 3 smaller stats stacked
    const stats = [
      { num: "5",  label: "APPS DEPLOYED",  sub: "Planner · Hub · Detailing · Dispatch · Install" },
      { num: "78", label: "LIVE JOBS",      sub: "Running on the platform today" },
      { num: "1",  label: "SOURCE OF TRUTH", sub: "All five apps, one database" }
    ];
    const rX = 5.4, rY = 1.0, rW = 4.2, rH = 1.15, rGap = 0.12;
    stats.forEach((st, i) => {
      const y = rY + i * (rH + rGap);
      s.addShape(pres.shapes.RECTANGLE, {
        x: rX, y, w: rW, h: rH,
        fill: { color: INK_ELEVATED }, line: { color: "2A2322", width: 0.5 },
        shadow: shadowCard()
      });
      s.addShape(pres.shapes.RECTANGLE, { x: rX, y, w: 0.05, h: rH, fill: { color: ACCENT }, line: { type: "none" } });
      s.addText(st.num, {
        x: rX + 0.25, y, w: 1.2, h: rH,
        fontFace: DISPLAY, fontSize: 72, color: ACCENT,
        align: "left", valign: "middle", margin: 0, bold: true
      });
      s.addText(st.label, {
        x: rX + 1.55, y: y + 0.22, w: rW - 1.7, h: 0.35,
        fontFace: DISPLAY, fontSize: 14, color: PAPER,
        align: "left", valign: "middle", charSpacing: 4, margin: 0
      });
      s.addText(st.sub, {
        x: rX + 1.55, y: y + 0.58, w: rW - 1.7, h: 0.5,
        fontFace: BODY_LIGHT, fontSize: 10, color: PAPER_MUTED,
        align: "left", valign: "top", margin: 0
      });
    });

    addPageCounter(s, 14);
  }

  // ---------- SLIDE 15 · NEXT 30 DAYS ----------
  {
    const s = pres.addSlide();
    s.background = { data: BG_CONTENT };
    addOverline(s, "15", "WHAT'S NEXT");

    s.addText("Next 30 days.", {
      x: M, y: 1.0, w: W - 2 * M, h: 1.0,
      fontFace: DISPLAY, fontSize: 68, color: PAPER,
      align: "left", valign: "middle", charSpacing: 2, margin: 0
    });

    const items = [
      { title: "Contractor PINs",   sub: "External crews log progress the same way supervisors do." },
      { title: "Customer sign-off", sub: "Client-side supervisors tick off deliveries on their phone." },
      { title: "Photo evidence",    sub: "Every claim backed by a dated, GPS-tagged photo." }
    ];
    const iX = M, iStartY = 2.35, iRowH = 0.85;
    items.forEach((it, i) => {
      const y = iStartY + i * (iRowH + 0.12);
      // Step number in mono
      s.addText(`0${i + 1}`, {
        x: iX, y, w: 0.6, h: 0.35,
        fontFace: MONO, fontSize: 10, color: ACCENT,
        align: "left", valign: "top", charSpacing: 3, margin: 0
      });
      // Hairline
      s.addShape(pres.shapes.RECTANGLE, {
        x: iX, y: y + 0.4, w: 0.5, h: 0.02, fill: { color: ACCENT }, line: { type: "none" }
      });
      // Title
      s.addText(it.title, {
        x: iX + 0.9, y, w: W - iX - 0.9 - M, h: 0.42,
        fontFace: DISPLAY, fontSize: 28, color: PAPER,
        align: "left", valign: "middle", charSpacing: 2, margin: 0
      });
      // Sub
      s.addText(it.sub, {
        x: iX + 0.9, y: y + 0.42, w: W - iX - 0.9 - M, h: 0.4,
        fontFace: BODY_LIGHT, fontSize: 13, color: PAPER_MUTED,
        align: "left", valign: "top", margin: 0
      });
    });

    addPageCounter(s, 15);
  }

  // ---------- SLIDE 16 · CLOSE ----------
  {
    const s = pres.addSlide();
    s.background = { data: BG_ACCENT };

    // Overline
    s.addShape(pres.shapes.RECTANGLE, { x: M, y: 0.65, w: 0.4, h: 0.03, fill: { color: INK }, line: { type: "none" } });
    s.addText("HYTEK FRAMING  ·  APRIL 2026", {
      x: M + 0.55, y: 0.55, w: 5, h: 0.25,
      fontFace: MONO, fontSize: 10, color: INK,
      align: "left", valign: "middle", charSpacing: 8, margin: 0
    });

    // Wordmark
    s.addText("HYTEK.", {
      x: M, y: 1.4, w: W - 2 * M, h: 2.3,
      fontFace: DISPLAY, fontSize: 260, color: INK,
      align: "left", valign: "middle", charSpacing: 8, margin: 0, bold: true
    });

    // Hairline + tagline
    s.addShape(pres.shapes.RECTANGLE, { x: M, y: 4.0, w: 0.6, h: 0.03, fill: { color: INK }, line: { type: "none" } });
    s.addText("Built for builders.", {
      x: M, y: 4.15, w: W - 2 * M, h: 0.5,
      fontFace: DISPLAY, fontSize: 32, color: INK,
      align: "left", valign: "middle", charSpacing: 8, margin: 0
    });
    s.addText("Scott Textor  ·  Operations Platform  ·  April 2026", {
      x: M, y: 4.65, w: W - 2 * M, h: 0.3,
      fontFace: BODY_LIGHT, fontSize: 11, color: INK,
      align: "left", valign: "middle", italic: true, margin: 0
    });

    s.addText("16 / 16", {
      x: W - 1.2, y: H - 0.4, w: 0.9, h: 0.2,
      fontFace: MONO, fontSize: 8, color: INK,
      align: "right", valign: "middle", charSpacing: 4, margin: 0
    });
  }

  await pres.writeFile({ fileName: "hytek-ops-platform-2026.pptx" });
  console.log("Wrote: hytek-ops-platform-2026.pptx");
}

main().catch(e => { console.error(e); process.exit(1); });
