/* Презентация защиты — КосмоХакатон 2026.
   Структура по рекомендации трекера: 6 основных слайдов + 5 backup для вопросов.
   Сборка: node build_deck.js -> kosmo-nizni_klodiki_148.pptx (16:9, статичные слайды). */
const path = require("path");
const globalRoot = "C:/Users/Administrator/AppData/Roaming/npm/node_modules";
const pptxgen = require(path.join(globalRoot, "pptxgenjs"));

const W = 13.33, H = 7.5, M = 0.6;
const BG_DARK = "0B1626", BG_LIGHT = "F4F7FA";
const PRIMARY = "14507E", PRIMARY_MID = "3B7AB8", PRIMARY_SOFT = "9FC0DC";
const ACCENT = "F2A007";
const TEXT_D = "16222E", TEXT_L = "EAF2F8", MUTED = "5B6B7C", MUTED_L = "8FA5B8";
const F = "Arial";

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";
pres.author = "Команда kosmo-nizni_klodiki_148";
pres.title = "Устойчивая спутниковая группировка — инженерный веб-сервис";

const IMG = (f) => path.join(__dirname, "img", f);

function orbit(slide, dark) {
  const c = dark ? PRIMARY_MID : PRIMARY_SOFT;
  slide.addShape(pres.shapes.OVAL, {
    x: W - 2.6, y: -1.5, w: 3.4, h: 2.4, fill: { type: "none" },
    line: { color: c, width: 1.2, transparency: dark ? 30 : 10 }, rotate: 18,
  });
  slide.addShape(pres.shapes.OVAL, {
    x: W - 1.28, y: 0.42, w: 0.14, h: 0.14, fill: { color: ACCENT }, line: { type: "none" },
  });
}

function titleBar(slide, kicker, title, dark) {
  slide.addText(kicker.toUpperCase(), {
    x: M, y: 0.42, w: 10, h: 0.32, fontFace: F, fontSize: 12, bold: true,
    color: dark ? PRIMARY_SOFT : PRIMARY_MID, charSpacing: 3, margin: 0,
  });
  slide.addText(title, {
    x: M, y: 0.74, w: 12.1, h: 0.75, fontFace: F, fontSize: 28, bold: true,
    color: dark ? TEXT_L : TEXT_D, margin: 0,
  });
}

function srcLine(slide, text, dark) {
  slide.addText(text, {
    x: M, y: H - 0.42, w: 12, h: 0.3, fontFace: F, fontSize: 11,
    color: dark ? MUTED_L : MUTED, margin: 0,
  });
}

/* ============================== 1. ТИТУЛЬНЫЙ ============================== */
let s = pres.addSlide();
s.background = { color: BG_DARK };
s.addShape(pres.shapes.OVAL, { x: 7.4, y: -3.4, w: 9.5, h: 9.5, fill: { type: "none" }, line: { color: PRIMARY_MID, width: 1.4, transparency: 35 } });
s.addShape(pres.shapes.OVAL, { x: 8.9, y: -1.9, w: 6.5, h: 6.5, fill: { type: "none" }, line: { color: PRIMARY_MID, width: 1.1, transparency: 55 } });
s.addShape(pres.shapes.OVAL, { x: 10.62, y: 1.62, w: 0.2, h: 0.2, fill: { color: ACCENT }, line: { type: "none" } });
s.addShape(pres.shapes.OVAL, { x: 8.05, y: 5.1, w: 0.13, h: 0.13, fill: { color: PRIMARY_SOFT }, line: { type: "none" } });
s.addText("КОСМОХАКАТОН 2026 · КЕЙС «ПРОЕКТИРОВАНИЕ УСТОЙЧИВОЙ СПУТНИКОВОЙ ГРУППИРОВКИ»", {
  x: M, y: 1.0, w: 11.6, h: 0.35, fontFace: F, fontSize: 12.5, bold: true, color: PRIMARY_SOFT, charSpacing: 2, margin: 0,
});
s.addText("Инженерный веб-сервис для проектирования\nи проверки устойчивости спутниковой группировки", {
  x: M, y: 1.5, w: 12.2, h: 2.0, fontFace: F, fontSize: 37, bold: true, color: TEXT_L, margin: 0, lineSpacing: 45,
});
s.addText("48 спутников · 3 очереди запуска · 3 северных пункта · 1 шлюз", {
  x: M, y: 3.7, w: 10.5, h: 0.4, fontFace: F, fontSize: 17, bold: true, color: ACCENT, margin: 0,
});
s.addText("Целевой уровень кейса: ≥90% времени со сквозным маршрутом для каждого пункта", {
  x: M, y: 4.18, w: 9.9, h: 0.4, fontFace: F, fontSize: 14.5, color: MUTED_L, margin: 0,
});
s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 10.15, y: 4.5, w: 2.45, h: 2.3, fill: { color: "FFFFFF" }, line: { type: "none" }, rectRadius: 0.06 });
s.addImage({ path: IMG("qr_service.png"), x: 10.33, y: 4.6, w: 2.1, h: 2.1 });
s.addText("Сервис открыт прямо сейчас —\nотсканируйте и попробуйте сами", {
  x: 10.0, y: 6.87, w: 2.75, h: 0.42, fontFace: F, fontSize: 10, color: PRIMARY_SOFT, margin: 0, align: "center",
});
s.addShape(pres.shapes.LINE, { x: M, y: 5.0, w: 3.2, h: 0, line: { color: ACCENT, width: 2.5 } });
s.addText([
  { text: "Команда kosmo-nizni_klodiki_148", options: { breakLine: true, bold: true, color: TEXT_L } },
  { text: "github.com/ivergit88/cosmohak", options: { color: PRIMARY_SOFT } },
], { x: M, y: 5.25, w: 9.2, h: 0.8, fontFace: F, fontSize: 14, margin: 0, paraSpaceAfter: 4 });

/* ============================== 2. ЧТО РЕШАЕТ ============================== */
s = pres.addSlide();
s.background = { color: BG_LIGHT };
orbit(s, false);
titleBar(s, "Задача", "Спутник над горизонтом ещё не означает, что связь есть");
s.addText([
  { text: "Услуга работает, только если в каждый момент есть полный маршрут:\n", options: { color: MUTED } },
  { text: "клиент → спутник → межспутниковая сеть → шлюз.", options: { bold: true, color: TEXT_D } },
], { x: M, y: 1.62, w: 12.1, h: 0.85, fontFace: F, fontSize: 17, margin: 0 });
const acts = [
  ["Проектируем", "Этап развёртывания, RAAN\nи фазирование, отказы —\nпроектные параметры до запуска", PRIMARY],
  ["Проверяем", "Сквозные маршруты по суткам на\n720 отсчётах; каждый разрыв имеет\nобъяснённую причину", PRIMARY],
  ["Выбираем", "Сравнение вариантов по доступности,\nперерывам и устойчивости —\nдо принятия решения", ACCENT],
];
acts.forEach((a, i) => {
  const x = M + i * 4.15;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: x, y: 2.75, w: 3.75, h: 2.9, fill: { color: "FFFFFF" }, line: { type: "none" },
    rectRadius: 0.08, shadow: { type: "outer", color: "1B2A3A", blur: 8, offset: 2, angle: 90, opacity: 0.14 },
  });
  s.addText(a[0], { x: x + 0.3, y: 3.05, w: 3.2, h: 0.5, fontFace: F, fontSize: 20, bold: true, color: a[2], margin: 0 });
  s.addText(a[1], { x: x + 0.3, y: 3.62, w: 3.2, h: 1.8, fontFace: F, fontSize: 13, color: TEXT_D, margin: 0, lineSpacing: 17 });
});
s.addText("Результаты выгружаются в официальном формате result JSON: один маршрут на каждую пару «отсчёт × пункт» (в базовом сценарии — 2160 записей).", {
  x: M, y: 6.0, w: 12.1, h: 0.4, fontFace: F, fontSize: 12, color: MUTED, margin: 0,
});
srcLine(s, "По документам кейса: постановка задачи, описание данных, критерии оценки", false);

/* ============================== 3. ПРОДУКТ ============================== */
s = pres.addSlide();
s.background = { color: BG_DARK };
titleBar(s, "Продукт", "Один экран: конфигурация → состояние сети → рекомендация", true);
s.addText("① Конфигурация            →        ② Сеть: маршрут или причина разрыва        →        ③ Доступность и рекомендация", {
  x: M, y: 1.58, w: 12.3, h: 0.3, fontFace: F, fontSize: 12, bold: true, color: PRIMARY_SOFT, margin: 0,
});
s.addImage({ path: IMG("crop_config.png"), x: M, y: 1.98, w: 1.95, h: 3.74 });
s.addShape(pres.shapes.RECTANGLE, { x: M, y: 1.98, w: 1.95, h: 3.74, fill: { type: "none" }, line: { color: PRIMARY_MID, width: 1 } });
s.addImage({ path: IMG("crop_network.png"), x: 2.8, y: 1.98, w: 7.07, h: 4.3 });
s.addShape(pres.shapes.RECTANGLE, { x: 2.8, y: 1.98, w: 7.07, h: 4.3, fill: { type: "none" }, line: { color: PRIMARY_MID, width: 1 } });
s.addImage({ path: IMG("crop_summary.png"), x: 2.8, y: 6.42, w: 5.6, h: 0.95 });
s.addShape(pres.shapes.RECTANGLE, { x: 2.8, y: 6.42, w: 5.6, h: 0.95, fill: { type: "none" }, line: { color: PRIMARY_MID, width: 1 } });
s.addText("Интерфейс на русском:\nскрытый сценарий жюри\nпроходит без правок кода", {
  x: 10.45, y: 2.3, w: 2.4, h: 1.6, fontFace: F, fontSize: 13, color: TEXT_L, margin: 0,
});
s.addText("3D-схема сети, шкала состояний\nпо всем пунктам, таблица метрик\nи рекомендация с цифрами", {
  x: 10.45, y: 4.1, w: 2.4, h: 2.2, fontFace: F, fontSize: 13, color: MUTED_L, margin: 0,
});

/* ============================== 4. РЕЗУЛЬТАТЫ ============================== */
s = pres.addSlide();
s.background = { color: BG_LIGHT };
orbit(s, false);
titleBar(s, "Результаты", "Полная группировка выдерживает цель — ранняя стадия и стресс-сценарии нет");
s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: M, y: 1.62, w: 12.13, h: 0.62, fill: { color: "E3F0E8" }, line: { type: "none" }, rectRadius: 0.06 });
s.addText([
  { text: "Базовая полная конфигурация: ", options: { color: TEXT_D } },
  { text: "3 из 3 пунктов выше целевых 90%", options: { bold: true, color: "2E7D32" } },
  { text: "  ·  доступность 96.7–98.9%", options: { color: TEXT_D } },
], { x: M + 0.3, y: 1.72, w: 11.6, h: 0.42, fontFace: F, fontSize: 15, margin: 0 });
s.addChart([
  {
    type: pres.charts.BAR,
    data: [
      { name: "C65", labels: ["Полная\nгруппировка", "1-я очередь", "10 отказов", "МСC 2000 км"], values: [96.67, 27.22, 79.31, 77.5] },
      { name: "C70", labels: ["Полная\nгруппировка", "1-я очередь", "10 отказов", "МСC 2000 км"], values: [98.75, 15.83, 80.83, 62.22] },
      { name: "C72", labels: ["Полная\nгруппировка", "1-я очередь", "10 отказов", "МСC 2000 км"], values: [98.89, 12.64, 82.5, 65.14] },
    ],
    options: { chartColors: [PRIMARY, PRIMARY_MID, ACCENT], barDir: "col", barGapWidthPct: 60 },
  },
  {
    type: pres.charts.LINE,
    data: [{ name: "Цель 90%", labels: ["Полная\nгруппировка", "1-я очередь", "10 отказов", "МСC 2000 км"], values: [90, 90, 90, 90] }],
    options: { chartColors: ["C62828"], lineSize: 2, lineDash: "dash", lineDataSymbol: "none" },
  },
], {
  x: M, y: 2.5, w: 7.6, h: 4.15,
  chartArea: { fill: { color: BG_LIGHT } },
  catAxisLabelColor: MUTED, valAxisLabelColor: MUTED, catAxisLabelFontSize: 11, valAxisLabelFontSize: 11,
  valAxisMaxVal: 100, valAxisMinVal: 0,
  valGridLine: { color: "DFE7EE", size: 0.5 }, catGridLine: { style: "none" },
  showLegend: true, legendPos: "b", legendColor: MUTED, legendFontSize: 11,
  showTitle: false, fontFace: F,
});
const outage = [
  ["Полная группировка (этап 3)", "96.7–98.9%", "перерывы 2–8 мин", "2E7D32"],
  ["Вторая очередь (этап 2)", "61.8–66.0%", "перерывы до 5.5 ч", "C62828"],
  ["Первая очередь (этап 1)", "12.6–27.2%", "перерывы до 13.3 ч", "C62828"],
  ["10 отказов · МСC 2000 км", "62.2–82.5%", "перерывы до 3 ч", "C62828"],
];
s.addText("Где цель достигается", { x: 8.6, y: 2.55, w: 4.2, h: 0.35, fontFace: F, fontSize: 15, bold: true, color: TEXT_D, margin: 0 });
outage.forEach((r, i) => {
  const y = 3.0 + i * 0.92;
  s.addText(r[0], { x: 8.6, y: y, w: 4.2, h: 0.3, fontFace: F, fontSize: 13, bold: true, color: TEXT_D, margin: 0 });
  s.addText([
    { text: r[1], options: { bold: true, color: r[3] } },
    { text: "  ·  " + r[2], options: { color: MUTED } },
  ], { x: 8.6, y: y + 0.3, w: 4.2, h: 0.3, fontFace: F, fontSize: 12, margin: 0 });
  if (i < 3) s.addShape(pres.shapes.LINE, { x: 8.6, y: y + 0.72, w: 4.1, h: 0, line: { color: "DFE7EE", width: 1 } });
});
srcLine(s, "Расчёт команды по официальному geometry.py: 720 отсчётов, стратегия «минимум длины»; числа зафиксированы регрессионными тестами", false);

/* ============================== 5. УСТОЙЧИВОСТЬ ============================== */
s = pres.addSlide();
s.background = { color: BG_LIGHT };
orbit(s, false);
titleBar(s, "Устойчивость", "Не только процент доступности — а почему сеть теряет связь");
s.addText("S44", { x: M, y: 1.9, w: 3.4, h: 1.25, fontFace: F, fontSize: 64, bold: true, color: ACCENT, margin: 0 });
s.addText([
  { text: "самый критичный аппарат\nпо single-outage анализу:\n", options: { bold: true, color: TEXT_D } },
  { text: "отказ снижает минимальную\nдоступность на 2.36 п.п., затрагивает\nвсе три пункта, 45 отсчётов теряют\nмаршрут", options: { color: MUTED } },
], { x: M, y: 3.2, w: 4.0, h: 2.2, fontFace: F, fontSize: 13, margin: 0, lineSpacing: 16 });
s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 4.95, y: 1.8, w: 7.8, h: 4.8, fill: { color: "FFFFFF" }, line: { type: "none" }, rectRadius: 0.08, shadow: { type: "outer", color: "1B2A3A", blur: 8, offset: 2, angle: 90, opacity: 0.14 } });
s.addText("Что видит инженер", { x: 5.3, y: 2.05, w: 7.1, h: 0.4, fontFace: F, fontSize: 16, bold: true, color: TEXT_D, margin: 0 });
const resRows = [
  ["Каждый разрыв объяснён", "нет видимого спутника · шлюз в отказе · нет контакта шлюза · разрыв межспутниковой сети"],
  ["Отказ аппарата — сразу эффект", "перестроение маршрута или новый перерыв с точным интервалом [начало; конец)"],
  ["Последствия по каждому пункту", "Δ доступности и перерывов до и после отказа — ещё до принятия решения"],
  ["Запас прочности", "резервные маршруты, не пересекающиеся с основным, и их доля по времени"],
];
resRows.forEach((r, i) => {
  const y = 2.6 + i * 0.98;
  s.addShape(pres.shapes.OVAL, { x: 5.3, y: y + 0.07, w: 0.13, h: 0.13, fill: { color: i === 0 ? ACCENT : PRIMARY }, line: { type: "none" } });
  s.addText(r[0], { x: 5.62, y: y - 0.06, w: 6.8, h: 0.34, fontFace: F, fontSize: 14.5, bold: true, color: TEXT_D, margin: 0 });
  s.addText(r[1], { x: 5.62, y: y + 0.28, w: 6.85, h: 0.6, fontFace: F, fontSize: 12, color: MUTED, margin: 0 });
});
srcLine(s, "Топ уязвимостей считается за один проход по сетке, без пересчёта орбитальной геометрии", false);

/* ============================== 6. ФИНАЛ ============================== */
s = pres.addSlide();
s.background = { color: BG_DARK };
s.addShape(pres.shapes.OVAL, { x: -3.2, y: 2.4, w: 9.5, h: 9.5, fill: { type: "none" }, line: { color: PRIMARY_MID, width: 1.3, transparency: 40 } });
s.addText("РЕЗУЛЬТАТ", { x: M, y: 0.95, w: 10, h: 0.35, fontFace: F, fontSize: 13, bold: true, color: PRIMARY_SOFT, charSpacing: 3, margin: 0 });
const res = [
  ["3 из 3", "пунктов выше целевого\nуровня в базовой полной\nконфигурации"],
  ["4 из 4", "категорий причин разрыва —\nкаждый перерыв имеет\nобъяснение"],
  ["A vs B", "конфигурации и отказы\nсравниваются до принятия\nрешения"],
];
res.forEach((r, i) => {
  const x = M + i * 3.2;
  s.addText(r[0], { x: x, y: 1.4, w: 2.95, h: 0.85, fontFace: F, fontSize: 38, bold: true, color: ACCENT, margin: 0 });
  s.addText(r[1], { x: x, y: 2.3, w: 2.95, h: 1.0, fontFace: F, fontSize: 12.5, color: TEXT_L, margin: 0 });
});
s.addShape(pres.shapes.LINE, { x: M, y: 3.45, w: 12.1, h: 0, line: { color: PRIMARY_MID, width: 1 } });
s.addText("РЕКОМЕНДАЦИЯ", { x: M, y: 3.7, w: 10, h: 0.35, fontFace: F, fontSize: 13, bold: true, color: PRIMARY_SOFT, charSpacing: 3, margin: 0 });
s.addText("Среди исследованных сценариев и проверенных конфигураций ≥90%\nдля всех трёх пунктов обеспечивает полная группировка при ISL 3000 км", {
  x: M, y: 4.08, w: 9.4, h: 1.2, fontFace: F, fontSize: 22, bold: true, color: TEXT_L, margin: 0, lineSpacing: 28,
});
s.addText("96.7–98.9% доступности  ·  каждый разрыв воспроизводим в сервисе и в тестах", {
  x: M, y: 5.32, w: 9.4, h: 0.4, fontFace: F, fontSize: 14, color: MUTED_L, margin: 0,
});
s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 10.15, y: 4.75, w: 2.35, h: 2.35, fill: { color: "FFFFFF" }, line: { type: "none" }, rectRadius: 0.06 });
s.addImage({ path: IMG("qr_service.png"), x: 10.28, y: 4.88, w: 2.1, h: 2.1 });
s.addText([
  { text: "Команда kosmo-nizni_klodiki_148  ·  ", options: { color: TEXT_L, bold: true } },
  { text: "github.com/ivergit88/cosmohak  ·  gitverse.ru/hackrus.experts/kosmo-nizni_klodiki_148", options: { color: PRIMARY_SOFT } },
], { x: M, y: 6.1, w: 9.4, h: 0.4, fontFace: F, fontSize: 12.5, margin: 0 });
s.addText("Спасибо! Вопросы?", { x: M, y: 6.55, w: 9.0, h: 0.5, fontFace: F, fontSize: 20, bold: true, color: TEXT_L, margin: 0 });

/* ============================== BACKUP 1: АЛГОРИТМ ============================== */
s = pres.addSlide();
s.background = { color: BG_LIGHT };
orbit(s, false);
titleBar(s, "Backup · Алгоритм", "Официальная геометрия → граф → маршрут → объяснение");
const chain = ["Официальная геометрия\nорганизаторов (geometry.py)", "Динамический граф сети\nна каждом отсчёте", "Сквозной маршрут\nминимальной длины", "Доступность + причина\nкаждого разрыва"];
chain.forEach((c, i) => {
  const x = M + i * 3.12;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: x, y: 2.0, w: 2.75, h: 1.5, fill: { color: "FFFFFF" }, line: { color: PRIMARY_SOFT, width: 1 }, rectRadius: 0.07 });
  s.addText(c, { x: x + 0.18, y: 2.15, w: 2.4, h: 1.2, fontFace: F, fontSize: 13.5, bold: true, color: TEXT_D, margin: 0 });
  if (i < 3) s.addText("→", { x: x + 2.7, y: 2.5, w: 0.5, h: 0.5, fontFace: F, fontSize: 22, bold: true, color: ACCENT, margin: 0, align: "center" });
});
s.addText([
  { text: "Маршрут по реальной геометрии сети. ", options: { bold: true, color: TEXT_D, breakLine: true } },
  { text: "На каждом временном шаге строится актуальный граф, маршрут минимизирует суммарную геометрическую длину; при равенстве результат детерминирован. Baseline — минимум переходов (BFS): достижимость идентична, различается конкретный путь.", options: { color: MUTED } },
], { x: M, y: 3.85, w: 12.1, h: 1.1, fontFace: F, fontSize: 14, margin: 0, paraSpaceAfter: 4 });
s.addText([
  { text: "Проверка корректности: ", options: { bold: true, color: TEXT_D } },
  { text: "официальный движок + независимая parity-реализация по формулам «Описания данных» — координаты, активность, связи и углы возвышения совпадают в тестах. Границы отказов [start; end), сетка 0…horizon без правого конца.", options: { color: MUTED } },
], { x: M, y: 5.05, w: 12.1, h: 1.1, fontFace: F, fontSize: 14, margin: 0 });
s.addText("Продолжение цепочки: анализ причин → критичность → рекомендация — всё на той же официальной модели.", {
  x: M, y: 6.25, w: 12.1, h: 0.4, fontFace: F, fontSize: 13, color: TEXT_D, margin: 0,
});

/* ============================== BACKUP 2: КАЧЕСТВО ============================== */
s = pres.addSlide();
s.background = { color: BG_LIGHT };
orbit(s, false);
titleBar(s, "Backup · Качество", "Проверяемо, воспроизводимо, запускается одной командой");
const q = [
  { n: "131", t: "автотест: валидация (44 граничных\nкейса), маршрутизация, метрики,\nэкспорт, интерфейс", c: PRIMARY },
  { n: "2", t: "реализации геометрии: официальная\nи независимая — parity-тесты\nсовпадения", c: PRIMARY },
  { n: "clean", t: "запуск по README на свежем venv:\npip install → streamlit run —\nпроверено, HTTP 200", c: ACCENT },
  { n: "1", t: "команда Docker: образ собирается\nи работает без API-ключей\nи внешних сервисов", c: PRIMARY },
];
q.forEach((it, i) => {
  const x = M + i * 3.12;
  s.addText(it.n, { x: x, y: 1.9, w: 2.8, h: 1.0, fontFace: F, fontSize: 46, bold: true, color: it.c, margin: 0 });
  s.addText(it.t, { x: x, y: 2.95, w: 2.85, h: 1.2, fontFace: F, fontSize: 12.5, color: MUTED, margin: 0 });
});
s.addShape(pres.shapes.LINE, { x: M, y: 4.35, w: W - 2 * M, h: 0, line: { color: PRIMARY_SOFT, width: 1 } });
s.addText("Воспроизводимость", { x: M, y: 4.55, w: 6, h: 0.4, fontFace: F, fontSize: 16, bold: true, color: TEXT_D, margin: 0 });
const repro = [
  "регрессионные числа зафиксированы тестами по всем четырём сценариям кейса",
  "повторные расчёты детерминированы: те же входные данные — тот же результат",
  "requirements зафиксированы точными версиями; абсолютных путей в коде нет",
];
s.addText(repro.map((t, i) => ({ text: t, options: { bullet: { code: "25B8", indent: 12 }, breakLine: i < repro.length - 1 } })), {
  x: M, y: 5.0, w: 12.1, h: 1.6, fontFace: F, fontSize: 14.5, color: TEXT_D, paraSpaceAfter: 8, margin: 0,
});

/* ============================== BACKUP 3: ЭКСПОРТ ============================== */
s = pres.addSlide();
s.background = { color: BG_LIGHT };
orbit(s, false);
titleBar(s, "Backup · Экспорт", "Строгий официальный формат — и отдельный файл анализа");
s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: M, y: 1.85, w: 5.9, h: 4.6, fill: { color: "0E1B2A" }, line: { type: "none" }, rectRadius: 0.08 });
s.addText([
  { text: '{\n', options: { color: PRIMARY_SOFT, breakLine: true } },
  { text: '  "schema_version": ', options: { color: PRIMARY_SOFT } },
  { text: '"cosmo-A-result-1.0",', options: { color: "9CCC82", breakLine: true } },
  { text: '  "effective_scenario": { ... },', options: { color: PRIMARY_SOFT, breakLine: true } },
  { text: '  "routes": [', options: { color: PRIMARY_SOFT, breakLine: true } },
  { text: '    { "t_s": 120, "client_id": "...",', options: { color: PRIMARY_SOFT, breakLine: true } },
  { text: '      "path": ["...", "...", "..."] },', options: { color: PRIMARY_SOFT, breakLine: true } },
  { text: '    ...', options: { color: PRIMARY_SOFT, breakLine: true } },
  { text: '  ]', options: { color: PRIMARY_SOFT, breakLine: true } },
  { text: '}', options: { color: PRIMARY_SOFT } },
], { x: M + 0.35, y: 2.1, w: 5.3, h: 3.8, fontFace: "Consolas", fontSize: 13, margin: 0, lineSpacing: 17 });
s.addText("result.json — ровно обязательные поля, без дополнений: структура критична", {
  x: M + 0.35, y: 5.95, w: 5.4, h: 0.5, fontFace: F, fontSize: 11.5, color: MUTED, margin: 0,
});
const expRows = [
  ["Одна запись на «отсчёт × пункт»", "пустой path — маршрут отсутствует; в базовом сценарии 2160 записей"],
  ["effective_scenario — весь сценарий", "включая все изменения пользователя; повторно загружается сервисом"],
  ["analysis_report.json — отдельно", "сводки, стратегия маршрутизации, интервалы перерывов с причинами"],
  ["Проверено тестами", "число записей, валидность каждого пути в свой момент, реимпорт сценария"],
];
expRows.forEach((r, i) => {
  const y = 1.95 + i * 1.12;
  s.addShape(pres.shapes.OVAL, { x: 6.95, y: y + 0.07, w: 0.13, h: 0.13, fill: { color: PRIMARY }, line: { type: "none" } });
  s.addText(r[0], { x: 7.27, y: y - 0.06, w: 5.5, h: 0.34, fontFace: F, fontSize: 14.5, bold: true, color: TEXT_D, margin: 0 });
  s.addText(r[1], { x: 7.27, y: y + 0.28, w: 5.5, h: 0.7, fontFace: F, fontSize: 12, color: MUTED, margin: 0 });
});

/* ============================== BACKUP 4: КРИТИЧНОСТЬ И РЕЗЕРВ ============================== */
s = pres.addSlide();
s.background = { color: BG_LIGHT };
orbit(s, false);
titleBar(s, "Backup · Критичность и резерв", "Single points of failure и запас прочности сети");
s.addText("Топ критичности (полная группировка, single-outage анализ)", { x: M, y: 1.75, w: 7.0, h: 0.4, fontFace: F, fontSize: 15, bold: true, color: TEXT_D, margin: 0 });
const crit = [
  ["S44", "Δmin 2.36 п.п.", "Δmean 2.08 п.п.", "45 отсчётов"],
  ["S45", "Δmin 2.36 п.п.", "Δmean 1.99 п.п.", "43 отсчёта"],
  ["S33", "Δmin 2.36 п.п.", "Δmean 1.94 п.п.", "42 отсчёта"],
];
crit.forEach((r, i) => {
  const y = 2.3 + i * 0.78;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: M, y: y, w: 6.9, h: 0.62, fill: { color: i === 0 ? "FFF7E6" : "FFFFFF" }, line: { color: "DFE7EE", width: 1 }, rectRadius: 0.05 });
  s.addText(r[0], { x: M + 0.25, y: y + 0.13, w: 1.0, h: 0.36, fontFace: F, fontSize: 15, bold: true, color: i === 0 ? "C77800" : TEXT_D, margin: 0 });
  s.addText(r[1] + "   ·   " + r[2] + "   ·   теряют маршрут " + r[3], { x: M + 1.3, y: y + 0.15, w: 5.4, h: 0.36, fontFace: F, fontSize: 12.5, color: MUTED, margin: 0 });
});
s.addText("Все три пункта затронуты у каждого из лидеров. Кнопка «применить отказ» переносит виртуальный отказ в сценарий — инженер сразу видит перестроение.", {
  x: M, y: 4.85, w: 6.9, h: 1.0, fontFace: F, fontSize: 13, color: TEXT_D, margin: 0,
});
s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 7.85, y: 1.75, w: 4.9, h: 4.75, fill: { color: "FFFFFF" }, line: { type: "none" }, rectRadius: 0.08, shadow: { type: "outer", color: "1B2A3A", blur: 8, offset: 2, angle: 90, opacity: 0.14 } });
s.addText("Резервные пути", { x: 8.15, y: 2.0, w: 4.3, h: 0.4, fontFace: F, fontSize: 16, bold: true, color: TEXT_D, margin: 0 });
const bk = [
  "ищется путь, не пересекающийся с основным по спутникам (node-disjoint)",
  "доля времени с резервом — метрика запаса прочности каждого пункта",
  "в базовом сценарии резерв существует в 17–38% подключённого времени",
  "переключения маршрутов считаются аналитикой (route changes), на доступность не влияют",
];
s.addText(bk.map((t, i) => ({ text: t, options: { bullet: { code: "25B8", indent: 12 }, breakLine: i < bk.length - 1 } })), {
  x: 8.15, y: 2.5, w: 4.35, h: 3.7, fontFace: F, fontSize: 13, color: TEXT_D, paraSpaceAfter: 10, margin: 0,
});

/* ============================== BACKUP 5: РАЗВИТИЕ ============================== */
s = pres.addSlide();
s.background = { color: BG_LIGHT };
orbit(s, false);
titleBar(s, "Backup · Развитие", "Что не входит в базовую модель — и следующий шаг");
s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: M, y: 1.9, w: 5.9, h: 4.4, fill: { color: "FFFFFF" }, line: { type: "none" }, rectRadius: 0.08, shadow: { type: "outer", color: "1B2A3A", blur: 8, offset: 2, angle: 90, opacity: 0.14 } });
s.addText("За рамками базовой модели", { x: M + 0.35, y: 2.15, w: 5.2, h: 0.4, fontFace: F, fontSize: 16, bold: true, color: TEXT_D, margin: 0 });
const notIn = [
  "рельеф и локальный горизонт пунктов",
  "городская застройка и локальные препятствия",
  "многолучёвость и радиочастотный бюджет",
  "энергетика (вспомогательная функция sunlight вне рамок кейса)",
  "stateful handover — по разъяснению эксперта независимый выбор маршрута на каждом шаге достаточен",
];
s.addText(notIn.map((t, i) => ({ text: t, options: { bullet: { code: "2013", indent: 12 }, breakLine: i < notIn.length - 1 } })), {
  x: M + 0.35, y: 2.65, w: 5.25, h: 3.4, fontFace: F, fontSize: 13, color: TEXT_D, paraSpaceAfter: 10, margin: 0,
});
s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 6.85, y: 1.9, w: 5.9, h: 4.4, fill: { color: "FFF7E6" }, line: { type: "none" }, rectRadius: 0.08 });
s.addText("Следующий этап", { x: 7.2, y: 2.15, w: 5.2, h: 0.4, fontFace: F, fontSize: 16, bold: true, color: TEXT_D, margin: 0 });
s.addText([
  { text: "Site-specific horizon mask", options: { bold: true, color: TEXT_D, breakLine: true } },
  { text: "локальная маска горизонта для каждого пункта поверх официальной модели возвышения — рельеф и urban obstruction без изменения ядра орбитальной модели.", options: { color: TEXT_D } },
], { x: 7.2, y: 2.65, w: 5.25, h: 1.7, fontFace: F, fontSize: 13, margin: 0, paraSpaceAfter: 6 });
s.addText([
  { text: "Уже готово к этому: ", options: { bold: true, color: TEXT_D } },
  { text: "движок принимает любые environment-значения из JSON, валидация изолирована, регрессионные тесты не дадут тихо изменить официальную модель.", options: { color: TEXT_D } },
], { x: 7.2, y: 4.5, w: 5.25, h: 1.6, fontFace: F, fontSize: 13, margin: 0 });
srcLine(s, "Рельеф/застройка упомянуты постановщиком как развитие и не влияют на текущие критерии оценки", false);

pres.writeFile({ fileName: path.join(__dirname, "kosmo-nizni_klodiki_148.pptx") }).then(() => console.log("OK: kosmo-nizni_klodiki_148.pptx"));
