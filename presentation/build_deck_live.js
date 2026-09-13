// Презентация для ЖИВОЙ защиты — стиль крупных утверждений (6 основных + 5 backup).
// Сборка: node build_deck_live.js -> kosmo-nizni_klodiki_148_live.pptx
const path = require("path");
const fs = require("fs");
const globalRoot = "C:/Users/Administrator/AppData/Roaming/npm/node_modules";
const pptxgen = require(path.join(globalRoot, "pptxgenjs"));

const W = 13.33, H = 7.5, M = 0.7;
const BG = "12172E", PANEL = "1B2240", PANEL2 = "232B52";
const ACCENT = "9BA3F5", ACCENT2 = "C9CFFA", DEEP = "6E76D6";
const WHITE = "F2F4FF", MUTED = "9AA3C7", GREEN = "7BD88F", RED = "E87A7A";
const F = "Arial";
const STAND = "https://qq27.tail293287.ts.net";
const REPO = "gitverse.ru/hackrus.experts/kosmo-nizni_klodiki_148";

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";
pres.author = "КосмоХакатон 2026 · команда Клодики";
pres.title = "Устойчивая спутниковая группировка — защита";

const IMG = (f) => path.join(__dirname, "img", f);
const line = (s, x, y, w) => s.addShape(pres.shapes.LINE, { x, y, w, h: 0, line: { color: DEEP, width: 1 } });

function kicker(s, text, y) {
  s.addText(text.toUpperCase(), { x: M, y: y, w: 11.9, h: 0.35, fontFace: F, fontSize: 13, bold: true, color: ACCENT, charSpacing: 3, margin: 0 });
}
function huge(s, text, y, size, w) {
  s.addText(text, { x: M, y: y, w: w || 12.0, h: size >= 40 ? 1.9 : 1.2, fontFace: F, fontSize: size, bold: true, color: WHITE, margin: 0, lineSpacing: size * 1.18 });
}
function note(s, text, y, w) {
  s.addText(text, { x: M, y: y, w: w || 11.9, h: 0.75, fontFace: F, fontSize: 15, color: ACCENT2, margin: 0 });
}
function foot(s, extra) {
  s.addText((extra ? extra + "   ·   " : "") + "КосмоХакатон 2026 · команда Клодики   ·   " + REPO, {
    x: M, y: H - 0.45, w: 12, h: 0.3, fontFace: F, fontSize: 10.5, color: MUTED, margin: 0,
  });
}
function stat(s, x, y, w, num, label, color, numSize) {
  s.addText(num, { x, y, w, h: 1.0, fontFace: F, fontSize: numSize || 52, bold: true, color: color || ACCENT, margin: 0 });
  s.addText(label, { x, y: y + 1.02, w, h: 0.85, fontFace: F, fontSize: 13, color: WHITE, margin: 0, lineSpacing: 16 });
}

/* ============================ 1. ТИТУЛ ============================ */
let s = pres.addSlide();
s.background = { path: IMG("bg_content.png") };
s.addShape(pres.shapes.LINE, { x: M, y: 0.9, w: 0.9, h: 0, line: { color: ACCENT, width: 2.5 } });
s.addText("КОСМОХАКАТОН 2026 · КЕЙС «ПРОЕКТИРОВАНИЕ УСТОЙЧИВОЙ СПУТНИКОВОЙ ГРУППИРОВКИ»", {
  x: M, y: 1.1, w: 11.9, h: 0.35, fontFace: F, fontSize: 12.5, bold: true, color: MUTED, charSpacing: 2, margin: 0,
});
huge(s, "Устойчивая спутниковая\nгруппировка: проектирование,\nотказы, рекомендация", 1.65, 40);
s.addText("Инженерный веб-сервис: считает доступность связи северных пунктов,\nобъясняет каждый разрыв и подбирает конфигурацию", {
  x: M, y: 4.15, w: 9.6, h: 0.8, fontFace: F, fontSize: 15, color: ACCENT2, margin: 0,
});
s.addText("48 спутников · 3 плоскости · 3 очереди · 3 пункта · 1 шлюз", {
  x: M, y: 5.05, w: 9.5, h: 0.4, fontFace: F, fontSize: 16, bold: true, color: WHITE, margin: 0,
});
// QR живого стенда
s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 10.35, y: 5.25, w: 2.3, h: 2.0, fill: { color: "FFFFFF" }, line: { type: "none" }, rectRadius: 0.06 });
s.addImage({ path: IMG("qr_service.png"), x: 10.52, y: 5.37, w: 1.76, h: 1.76 });
s.addText("стенд открыт — проверьте с телефона", {
  x: 10.1, y: 7.28, w: 2.8, h: 0.2, fontFace: F, fontSize: 8.5, color: MUTED, margin: 0, align: "center",
});
s.addText([
  { text: REPO, options: { color: ACCENT2, breakLine: true } },
  { text: "стенд: " + STAND.replace("https://", ""), options: { color: MUTED } },
], { x: M, y: 6.3, w: 9.3, h: 0.7, fontFace: F, fontSize: 13, margin: 0, paraSpaceAfter: 4 });

/* ============================ 2. ПРОБЛЕМА ============================ */
s = pres.addSlide();
s.background = { path: IMG("bg_content.png") };
kicker(s, "Проблема", 0.75);
huge(s, "Спутник над горизонтом ещё\nне означает, что связь есть", 1.15, 36);
s.addText([
  { text: "Связь есть только когда в момент времени t существует полный путь:", options: { color: ACCENT2, breakLine: true } },
  { text: "клиент → спутник → межспутниковая сеть → шлюз", options: { bold: true, color: WHITE, breakLine: true } },
  { text: "Например, при ISL 2000 км клиент видит спутник почти все сутки, но сквозной маршрут существует лишь 62,22% времени.", options: { color: MUTED, breakLine: true } },
], { x: M, y: 3.3, w: 11.9, h: 0.85, fontFace: F, fontSize: 17, margin: 0, paraSpaceAfter: 4 });
const cards = [
  ["Проектируем", "этап развертывания 16/32/48,\nRAAN и фазирование плоскостей", DEEP],
  ["Проверяем", "сквозные маршруты на 720 отсчетов\nсуток; каждый разрыв — с причиной", DEEP],
  ["Выбираем", "сравнение вариантов по доступности,\nперерывам и устойчивости", ACCENT],
];
cards.forEach((c, i) => {
  const x = M + i * 4.05;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 4.45, w: 3.7, h: 2.15, fill: { color: PANEL }, line: { type: "none" }, rectRadius: 0.07 });
  s.addText(c[0], { x: x + 0.3, y: 4.7, w: 3.1, h: 0.45, fontFace: F, fontSize: 19, bold: true, color: i === 2 ? ACCENT : WHITE, margin: 0 });
  s.addText(c[1], { x: x + 0.3, y: 5.25, w: 3.15, h: 1.2, fontFace: F, fontSize: 12.5, color: ACCENT2, margin: 0, lineSpacing: 16 });
});
foot(s, "видимость спутника — необходимое, но не достаточное условие связи");

/* ============================ 3. ПРОДУКТ + ВИДЕО ============================ */
s = pres.addSlide();
s.background = { path: IMG("bg_content.png") };
kicker(s, "Продукт", 0.75);
huge(s, "Один сервис: конфигурация → состояние сети → рекомендация", 1.15, 27);
s.addText("видеозапись работы сервиса — 37 секунд, всё видно", {
  x: M, y: 2.35, w: 8.4, h: 0.3, fontFace: F, fontSize: 12.5, bold: true, color: ACCENT2, margin: 0,
});
s.addMedia({
  type: "video",
  path: path.join(__dirname, "demo_screencast.mp4"),
  x: M, y: 2.65, w: 8.0, h: 4.5,
  cover: "image/png;base64," + fs.readFileSync(path.join(__dirname, "poster_video.b64"), "utf-8").trim(),
});
s.addShape(pres.shapes.RECTANGLE, { x: M, y: 2.65, w: 8.0, h: 4.5, fill: { type: "none" }, line: { color: DEEP, width: 1 } });
s.addText("В записи:", { x: 9.35, y: 2.8, w: 3.3, h: 0.35, fontFace: F, fontSize: 13.5, bold: true, color: WHITE, margin: 0 });
const vidPts = [
  "карточки доступности\nпо каждому пункту",
  "3D-схема сети:\nспутники, связи, маршрут",
  "прыжок к перерыву —\nпричина разрыва",
  "шкала состояний\nза сутки по всем пунктам",
];
s.addText(vidPts.map((t, i) => ({ text: t, options: { bullet: { code: "25B8", indent: 12 }, breakLine: i < vidPts.length - 1 } })), {
  x: 9.35, y: 3.25, w: 3.3, h: 3.0, fontFace: F, fontSize: 12.5, color: WHITE, paraSpaceAfter: 10, margin: 0,
});
s.addText("▶ нажмите на видео при показе", { x: 9.35, y: 6.4, w: 3.3, h: 0.55, fontFace: F, fontSize: 11.5, color: MUTED, margin: 0 });

/* ============================ 4. РЕЗУЛЬТАТ ============================ */
s = pres.addSlide();
s.background = { path: IMG("bg_content.png") };
kicker(s, "Результат · базовые сценарии", 0.55);
huge(s, "Цель 90% держит\nтолько полная группировка", 0.95, 38);
const rows = [
  ["Полная группировка (этап 3)", "96,67 %", "98,75 %", "98,89 %", "8 мин", GREEN],
  ["Вторая очередь (этап 2)", "61,81 %", "62,50 %", "65,97 %", "5 ч 30 мин", RED],
  ["Первая очередь (этап 1)", "27,22 %", "15,83 %", "12,64 %", "13 ч 16 мин", RED],
  ["10 отказов с 6-го часа", "79,31 %", "80,83 %", "82,50 %", "24 мин", RED],
  ["ISL 2000 км", "77,50 %", "62,22 %", "65,14 %", "2 ч 58 мин", RED],
];
let ty = 2.75;
s.addText("СЦЕНАРИЙ", { x: M, y: ty, w: 4.4, h: 0.3, fontFace: F, fontSize: 11.5, bold: true, color: MUTED, charSpacing: 2, margin: 0 });
s.addText("C65", { x: 5.35, y: ty, w: 1.6, h: 0.3, fontFace: F, fontSize: 11.5, bold: true, color: MUTED, margin: 0 });
s.addText("C70", { x: 7.15, y: ty, w: 1.6, h: 0.3, fontFace: F, fontSize: 11.5, bold: true, color: MUTED, margin: 0 });
s.addText("C72", { x: 8.95, y: ty, w: 1.6, h: 0.3, fontFace: F, fontSize: 11.5, bold: true, color: MUTED, margin: 0 });
s.addText("ХУДШИЙ ПЕРЕРЫВ", { x: 10.55, y: ty, w: 2.4, h: 0.3, fontFace: F, fontSize: 11.5, bold: true, color: MUTED, margin: 0 });
ty += 0.42;
rows.forEach((r, i) => {
  s.addShape(pres.shapes.RECTANGLE, { x: M - 0.15, y: ty - 0.06, w: 12.3, h: 0.56, fill: { color: i === 0 ? PANEL2 : BG }, line: { type: "none" } });
  s.addText(r[0], { x: M, y: ty, w: 4.4, h: 0.4, fontFace: F, fontSize: 14.5, bold: i === 0, color: WHITE, margin: 0 });
  s.addText(r[1], { x: 5.35, y: ty, w: 1.7, h: 0.4, fontFace: F, fontSize: 14.5, bold: i === 0, color: r[5], margin: 0 });
  s.addText(r[2], { x: 7.15, y: ty, w: 1.7, h: 0.4, fontFace: F, fontSize: 14.5, color: WHITE, margin: 0 });
  s.addText(r[3], { x: 8.95, y: ty, w: 1.7, h: 0.4, fontFace: F, fontSize: 14.5, color: WHITE, margin: 0 });
  s.addText(r[4], { x: 10.55, y: ty, w: 2.3, h: 0.4, fontFace: F, fontSize: 14.5, color: WHITE, margin: 0 });
  ty += 0.62;
});
s.addText("Причины разные: на 1-й очереди над пунктом просто нет спутника,\nпри ISL 2000 км спутник виден, но сеть рвётся между плоскостями.", {
  x: M, y: 6.38, w: 11.9, h: 0.55, fontFace: F, fontSize: 14, color: ACCENT2, margin: 0,
});
foot(s, "официальный geometry.py · 720 отсчетов · стратегия «минимум длины» · числа зафиксированы регрессионными тестами");

/* ============================ 5. ISL ПОРОГ ============================ */
s = pres.addSlide();
s.background = { path: IMG("bg_content.png") };
kicker(s, "Результат · дальность межспутниковой связи", 0.55);
huge(s, "3000 км дают запас: целевой уровень держится\nпримерно с 2725 км", 0.95, 32);
stat(s, M, 2.85, 4.6, "~275 км", "запаса штатных 3000 км\nотносительно найденной границы", ACCENT, 60);
s.addText("На суточной сетке базовой полной конфигурации: 2700 км → 85,6%, 2725 км → 96,67%, 3000 км → 96,67%. Не универсальная граница — результат для данной геометрии и горизонта.", {
  x: M, y: 5.05, w: 4.5, h: 1.3, fontFace: F, fontSize: 12, color: MUTED, margin: 0 });
const sweepLabels = ["2000", "2100", "2200", "2300", "2400", "2500", "2600", "2700", "2725", "2800", "2900", "3000"];
const sweepAll = { 2000: 62.22, 2100: 65.28, 2200: 69.58, 2300: 72.64, 2400: 76.39, 2500: 79.44, 2600: 82.22, 2700: 85.56, 2725: 96.67, 2800: 96.67, 2900: 96.67, 3000: 96.67 };
s.addChart([
  { type: pres.charts.LINE, data: [{ name: "MIN доступность", labels: sweepLabels, values: sweepLabels.map(l => sweepAll[l]) }], options: { chartColors: [ACCENT], lineSize: 3, lineSmooth: false, lineDataSymbol: "circle", lineDataSymbolSize: 5 } },
  { type: pres.charts.LINE, data: [{ name: "цель 90%", labels: sweepLabels, values: sweepLabels.map(() => 90) }], options: { chartColors: [RED], lineSize: 1.5, lineDash: "dash", lineDataSymbol: "none" } },
], {
  x: 5.6, y: 2.45, w: 7.1, h: 3.95,
  chartArea: { fill: { color: BG } },
  catAxisLabelColor: MUTED, valAxisLabelColor: MUTED, catAxisLabelFontSize: 10.5, valAxisLabelFontSize: 10.5,
  valAxisMaxVal: 100, valAxisMinVal: 55,
  valGridLine: { color: PANEL2, size: 0.5 }, catGridLine: { style: "none" },
  showLegend: true, legendPos: "b", legendColor: MUTED, legendFontSize: 10.5,
  showTitle: false, fontFace: F,
});
s.addText([
  { text: "2700 км — 85,6 %   ·   ", options: { color: WHITE } },
  { text: "2725 км — 96,67 %", options: { bold: true, color: ACCENT } },
  { text: "   ·   3000 км — 96,67 %", options: { color: WHITE } },
], { x: 5.6, y: 6.52, w: 7.2, h: 0.32, fontFace: F, fontSize: 12, margin: 0 });
foot(s, "тот же официальный расчет: при снижении дальности до 2725 км доступность не меняется — запас требования 275 км");

/* ============================ 6. УСТОЙЧИВОСТЬ ============================ */
s = pres.addSlide();
s.background = { path: IMG("bg_content.png") };
kicker(s, "Результат · устойчивость", 0.55);
huge(s, "N-1: любой одиночный отказ\nсохраняет целевой уровень", 0.95, 32);
stat(s, M, 2.9, 4.0, "94,31%", "худшая минимальная доступность\nсреди 48 суточных одиночных отказов\n(48/48 проверено, цель ≥90% выполнена)", ACCENT, 54);
s.addText("Худший случай — S44 (№1 ранжирования критичности): \n−2,36 п.п. минимальной доступности, 45 клиент-отсчетов теряют маршрут. Самый загруженный (S45) — не самый критичный.", {
  x: M, y: 5.5, w: 4.0, h: 1.3, fontFace: F, fontSize: 12, color: MUTED, margin: 0,
});
s.addText("Что это дает инженеру", { x: 5.5, y: 2.85, w: 6.9, h: 0.4, fontFace: F, fontSize: 16, bold: true, color: WHITE, margin: 0 });
const rr = [
  ["Причина каждого разрыва", "4 категории: нет видимого спутника · шлюз в отказе · шлюз не видит сеть · разрыв ISL"],
  ["Отказ — сразу перестроение", "новый маршрут или новый перерыв с точным интервалом [начало; конец)"],
  ["48 N-1 прогонов на общей геометрии", "координаты и базовые контакты переиспользуются, маршруты пересчитываются для каждого отказа"],
  ["Резерв без общих спутников", "есть в 17–38% времени — метрика запаса прочности"],
];
rr.forEach((r, i) => {
  const y = 3.4 + i * 0.85;
  s.addShape(pres.shapes.OVAL, { x: 5.5, y: y + 0.06, w: 0.12, h: 0.12, fill: { color: i === 0 ? ACCENT : DEEP }, line: { type: "none" } });
  s.addText(r[0], { x: 5.8, y: y - 0.05, w: 6.6, h: 0.32, fontFace: F, fontSize: 14, bold: true, color: WHITE, margin: 0 });
  s.addText(r[1], { x: 5.8, y: y + 0.27, w: 6.7, h: 0.55, fontFace: F, fontSize: 11.5, color: ACCENT2, margin: 0 });
});

/* ============================ 7. ФИНАЛ ============================ */
s = pres.addSlide();
s.background = { path: IMG("bg_content.png") };
s.addShape(pres.shapes.LINE, { x: M, y: 0.85, w: 0.9, h: 0, line: { color: ACCENT, width: 2.5 } });
huge(s, "Мы не добавили ни одного спутника —\nнашли запас там, где он уже был", 1.05, 33);
stat(s, M, 3.1, 3.9, "96,67→98,33%", "мин. доступность после\nавтоподбора RAAN/фазирования\n(бюджет 40 прогонов)", ACCENT, 34);
stat(s, 4.75, 3.1, 3.9, "8→2 мин", "худший перерыв\nпосле автоподбора", WHITE, 44);
stat(s, 8.9, 3.1, 3.9, "48/48", "N-1: любой одиночный отказ\nвыше целевого уровня", WHITE, 44);
s.addShape(pres.shapes.LINE, { x: M, y: 5.15, w: 12.0, h: 0, line: { color: DEEP, width: 1 } });
s.addText([
  { text: "РЕКОМЕНДАЦИЯ:  ", options: { bold: true, color: ACCENT } },
  { text: "развертывать все три очереди; штатную дальность ISL 3000 км сохранять —\nпорог 2725 км оставляет 275 км запаса на бюджет радиолинии.", options: { color: WHITE } },
], { x: M, y: 5.35, w: 9.3, h: 0.85, fontFace: F, fontSize: 16, margin: 0, paraSpaceAfter: 4 });
s.addText("Лучший найденный кандидат в пределах бюджета поиска; глобальный оптимум не заявляется.", {
  x: M, y: 6.32, w: 9.3, h: 0.3, fontFace: F, fontSize: 11, color: MUTED, margin: 0 });
s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 10.35, y: 5.3, w: 2.3, h: 2.0, fill: { color: "FFFFFF" }, line: { type: "none" }, rectRadius: 0.06 });
s.addImage({ path: IMG("qr_service.png"), x: 10.52, y: 5.42, w: 1.76, h: 1.76 });
s.addText([
  { text: REPO + "  ·  стенд: " + STAND.replace("https://", ""), options: { color: ACCENT2 } },
], { x: M, y: 6.35, w: 9.4, h: 0.35, fontFace: F, fontSize: 12.5, margin: 0 });
s.addText("Спасибо! Вопросы?", { x: M, y: 7.12, w: 8.0, h: 0.45, fontFace: F, fontSize: 19, bold: true, color: WHITE, margin: 0 });

/* ============================ B1. АЛГОРИТМ ============================ */
s = pres.addSlide();
s.background = { path: IMG("bg_content.png") };
kicker(s, "Backup · Алгоритм", 0.75);
huge(s, "Кэш геометрии + фильтр состояния + 4 стратегии маршрутизации", 1.15, 28);
const alg = [
  ["Кэш геометрии — один раз на сценарий", "треки и маски линий считаются одним проходом"],
  ["Фильтр на каждом отсчете", "этап, отказы и шлюзы накладываются маской: линия живет, только если оба конца активны"],
  ["A* = weighted", "8640/8640 маршрутов совпали; 0 невалидных путей"],
  ["Смена самой геометрии", "изменения параметров подхватываются корректно"],
];
alg.forEach((a, i) => {
  const y = 3.45 + i * 0.82;
  s.addText(a[0], { x: M, y: y, w: 5.6, h: 0.34, fontFace: F, fontSize: 14.5, bold: true, color: ACCENT, margin: 0 });
  s.addText(a[1], { x: M + 0.25, y: y + 0.36, w: 5.6, h: 0.5, fontFace: F, fontSize: 11.5, color: ACCENT2, margin: 0 });
});
s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 7.0, y: 2.9, w: 5.7, h: 3.6, fill: { color: PANEL }, line: { type: "none" }, rectRadius: 0.07 });
s.addText("4 стратегии в интерфейсе", { x: 7.35, y: 3.15, w: 5.0, h: 0.4, fontFace: F, fontSize: 15.5, bold: true, color: WHITE, margin: 0 });
const strong = [
  "минимум длины — взвешенный поиск, по умолчанию",
  "A* с гео-эвристикой: тот же оптимум, раскрытий −93%",
  "минимум переходов — BFS, baseline",
  "жадная географическая — быстро, без гарантии",
];
s.addText(strong.map((t, i) => ({ text: t, options: { bullet: { code: "25B8", indent: 12 }, breakLine: i < strong.length - 1 } })), {
  x: 7.35, y: 3.65, w: 5.05, h: 2.2, fontFace: F, fontSize: 12.5, color: WHITE, paraSpaceAfter: 9, margin: 0,
});
s.addText("замер на суточном прогоне: A* раскрыл 1766 узлов против 25920 у полного перебора", {
  x: 7.35, y: 5.85, w: 5.05, h: 0.6, fontFace: F, fontSize: 11.5, color: ACCENT2, margin: 0,
});
foot(s, "геометрия — официальный модуль организаторов; независимая реализация формул используется только для parity-проверки");

/* ============================ B2. КАЧЕСТВО ============================ */
s = pres.addSlide();
s.background = { path: IMG("bg_content.png") };
kicker(s, "Backup · Качество", 0.75);
huge(s, "133 теста: границы, маршруты,\nэкспорт, интерфейс", 1.15, 34);
stat(s, M, 3.3, 3.9, "133", "теста проходят:\nвалидация (46 граничных\nкейсов), маршрутизация,\nметрики, экспорт, UI", ACCENT, 46);
stat(s, 4.75, 3.3, 3.9, "clean", "запуск по README на свежем venv:\npip install → streamlit run —\nпроверено, HTTP 200", WHITE, 46);
stat(s, 8.9, 3.3, 3.9, "Docker", "контейнер с автоперезапуском;\nзависимости зафиксированы\nточными версиями", WHITE, 46);
s.addShape(pres.shapes.LINE, { x: M, y: 5.6, w: 12.0, h: 0, line: { color: DEEP, width: 1 } });
s.addText("Воспроизводимость: те же входные данные — тот же результат. Экспортируемый effective scenario загружается обратно и проходит ту же валидацию.", {
  x: M, y: 5.8, w: 12.0, h: 0.6, fontFace: F, fontSize: 14.5, color: ACCENT2, margin: 0,
});
foot(s);

/* ============================ B3. ЭКСПОРТ ============================ */
s = pres.addSlide();
s.background = { path: IMG("bg_content.png") };
kicker(s, "Backup · Экспорт", 0.75);
huge(s, "Минимальный официальный формат +\nотдельный файл анализа", 1.15, 30);
s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: M, y: 2.6, w: 5.9, h: 3.6, fill: { color: PANEL }, line: { type: "none" }, rectRadius: 0.07 });
s.addText([
  { text: '{\n', options: { color: ACCENT2, breakLine: true } },
  { text: '  "schema_version": ', options: { color: ACCENT2 } },
  { text: '"cosmo-A-result-1.0",', options: { color: ACCENT, breakLine: true } },
  { text: '  "effective_scenario": { ... },', options: { color: ACCENT2, breakLine: true } },
  { text: '  "routes": [ ... ]', options: { color: ACCENT2, breakLine: true } },
  { text: '}', options: { color: ACCENT2 } },
], { x: M + 0.35, y: 2.85, w: 5.2, h: 2.6, fontFace: "Consolas", fontSize: 14, margin: 0, lineSpacing: 19 });
s.addText("только обязательные поля; расширенная аналитика —\nв analysis_report.json", {
  x: M + 0.35, y: 5.5, w: 5.4, h: 0.55, fontFace: F, fontSize: 11.5, color: MUTED, margin: 0,
});
const exp = [
  ["2160 записей", "720 отсчетов × 3 пункта — на каждую пару t_s × client_id ровно одна"],
  ["Пустой path = маршрута нет", "причина разрыва — в analysis_report"],
  ["Реимпорт", "effective_scenario загружается обратно и проходит полную валидацию"],
];
exp.forEach((r, i) => {
  const y = 2.7 + i * 1.15;
  s.addShape(pres.shapes.OVAL, { x: 7.0, y: y + 0.06, w: 0.12, h: 0.12, fill: { color: ACCENT }, line: { type: "none" } });
  s.addText(r[0], { x: 7.3, y: y - 0.05, w: 5.4, h: 0.35, fontFace: F, fontSize: 14.5, bold: true, color: WHITE, margin: 0 });
  s.addText(r[1], { x: 7.3, y: y + 0.3, w: 5.4, h: 0.65, fontFace: F, fontSize: 12, color: ACCENT2, margin: 0 });
});
foot(s);

/* ============================ B4. КРИТИЧНОСТЬ ============================ */
s = pres.addSlide();
s.background = { path: IMG("bg_content.png") };
kicker(s, "Backup · Критичность", 0.75);
huge(s, "Критичные аппараты при одиночном отказе:\nleave-one-out по всем 48", 1.15, 28);
const crit = [
  ["S44", "№1 критичности", "Δmin 2,36 п.п.", "45 клиент-отсчетов"],
  ["S45", "№2, самый загруженный", "Δmin 2,36 п.п.", "43 клиент-отсчета"],
  ["S16", "№3", "Δmin 2,36 п.п.", "42 клиент-отсчета"],
];
crit.forEach((r, i) => {
  const y = 2.9 + i * 0.85;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: M, y: y, w: 7.2, h: 0.68, fill: { color: i === 0 ? PANEL2 : PANEL }, line: { type: "none" }, rectRadius: 0.05 });
  s.addText(r[0], { x: M + 0.3, y: y + 0.15, w: 1.1, h: 0.4, fontFace: F, fontSize: 16, bold: true, color: i === 0 ? ACCENT : WHITE, margin: 0 });
  s.addText(r[1], { x: M + 1.5, y: y + 0.18, w: 2.6, h: 0.36, fontFace: F, fontSize: 12.5, color: ACCENT2, margin: 0 });
  s.addText(r[2] + "  ·  " + r[3], { x: M + 4.2, y: y + 0.18, w: 3.6, h: 0.36, fontFace: F, fontSize: 12.5, color: WHITE, margin: 0 });
});
s.addText("Мы не называем лидера single point of failure: сеть после его отказа продолжает работать — но именно он создает наибольший риск для минимальной доступности.", {
  x: M, y: 5.65, w: 7.2, h: 0.95, fontFace: F, fontSize: 13, color: ACCENT2, margin: 0,
});
s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 8.35, y: 2.6, w: 4.35, h: 3.9, fill: { color: PANEL }, line: { type: "none" }, rectRadius: 0.07 });
s.addText("Резервные пути", { x: 8.7, y: 2.85, w: 3.7, h: 0.4, fontFace: F, fontSize: 15.5, bold: true, color: WHITE, margin: 0 });
const bk = [
  "второй путь без общих внутренних спутников с основным",
  "есть в 17–38% подключенного времени",
  "переключения маршрута — аналитика, не ограничение",
];
s.addText(bk.map((t, i) => ({ text: t, options: { bullet: { code: "25B8", indent: 12 }, breakLine: i < bk.length - 1 } })), {
  x: 8.7, y: 3.35, w: 3.75, h: 3.0, fontFace: F, fontSize: 12.5, color: WHITE, paraSpaceAfter: 10, margin: 0,
});
foot(s);

/* ============================ B5. РАЗВИТИЕ ============================ */
s = pres.addSlide();
s.background = { path: IMG("bg_content.png") };
kicker(s, "Backup · Развитие", 0.75);
huge(s, "Что за рамками базовой модели —\nи следующим шагом", 1.15, 30);
const dev = [
  ["Рельеф и застройка", "site-specific horizon mask поверх официальной модели возвышения — без изменения ядра"],
  ["Пропускная способность и задержки", "в исходной постановке нет данных каналов; добавляется расширением метрики"],
  ["Энергетика (sunlight)", "нет модели батарей и критерия энергетического отказа — не отключаем аппараты"],
  ["Большие группировки", "движок не хардкодит ID и координаты и работает со сценариями схемы cosmo-A-1.0"],
];
dev.forEach((r, i) => {
  const y = 2.75 + i * 1.05;
  s.addShape(pres.shapes.OVAL, { x: M, y: y + 0.06, w: 0.12, h: 0.12, fill: { color: i === 0 ? ACCENT : DEEP }, line: { type: "none" } });
  s.addText(r[0], { x: M + 0.3, y: y - 0.05, w: 11.5, h: 0.35, fontFace: F, fontSize: 14.5, bold: true, color: WHITE, margin: 0 });
  s.addText(r[1], { x: M + 0.3, y: y + 0.3, w: 11.6, h: 0.6, fontFace: F, fontSize: 12, color: ACCENT2, margin: 0 });
});
foot(s, "официальная модель воспроизводима: регрессионные тесты не дают тихо изменить расчет");

const OUT = process.argv[2] ? path.join(__dirname, process.argv[2]) : path.join(__dirname, "kosmo-nizni_klodiki_148_live.pptx");
pres.writeFile({ fileName: OUT }).then(() => console.log("OK: " + OUT));
