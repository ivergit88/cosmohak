// Скринкаст v3: плавные прокрутки, быстрый темп (~20 секунд демо).
const path = require("path");
const globalRoot = "C:/Users/Administrator/AppData/Roaming/npm/node_modules";
const { chromium } = require(path.join(globalRoot, "playwright"));

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({
    viewport: { width: 1280, height: 720 },
    recordVideo: { dir: path.join(__dirname, "vid"), size: { width: 1280, height: 720 } },
  });
  const page = await ctx.newPage();
  await page.goto("http://localhost:8501", { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(7000); // прогрев интерфейса

  // плавная прокрутка основного контейнера Streamlit (~0.35 с на ход)
  const scrollMain = async (y) => {
    await page.evaluate(async (target) => {
      const el = document.querySelector('[data-testid="stMain"]');
      const start = el.scrollTop;
      const t0 = performance.now();
      await new Promise((resolve) => {
        const step = (t) => {
          const k = Math.min(1, (t - t0) / 350);
          el.scrollTop = Math.round(start + (target - start) * k);
          if (k < 1) requestAnimationFrame(step);
          else resolve();
        };
        requestAnimationFrame(step);
      });
    }, y);
  };
  const clickRadio = (i) => page.evaluate(`document.querySelectorAll('input[type="radio"]')[${i}].click()`);
  const clickButton = (txt) => page.evaluate(`(() => {
    const b = [...document.querySelectorAll('button')].find(x => x.textContent.includes('${txt}'));
    if (b) b.click();
    return !!b;
  })()`);

  await scrollMain(0);
  await page.waitForTimeout(600);

  // 0-2.2с: обзор — карточки и сводка
  await page.waitForTimeout(2200);
  // прокрутка к графикам и таблице
  await scrollMain(950);
  await page.waitForTimeout(1700);
  // прокрутка к рекомендации
  await scrollMain(620);
  await page.waitForTimeout(1400);
  // наверх и вкладка «Сеть и время»
  await scrollMain(0);
  await page.waitForTimeout(500);
  await clickRadio(1);
  await page.waitForTimeout(3000);
  // 3D-схема с маршрутом
  await page.waitForTimeout(1200);
  // таймлайн
  await scrollMain(1500);
  await page.waitForTimeout(1800);
  // обратно к 3D
  await scrollMain(250);
  await page.waitForTimeout(900);
  // прыжок к перерыву — причина разрыва
  await clickButton("Перерыв ▶");
  await page.waitForTimeout(2600);
  // вкладка «Обзор» — рекомендация
  await clickRadio(0);
  await page.waitForTimeout(2200);
  await scrollMain(620);
  await page.waitForTimeout(1800);
  await scrollMain(0);
  await page.waitForTimeout(1200);

  await page.close();
  await browser.close();
  console.log("OK: скринкаст v3 записан");
})().catch((e) => { console.error("FAIL:", e.message); process.exit(1); });
