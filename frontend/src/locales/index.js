import { createI18n } from "vue-i18n";
import zh from "./zh.json";
import en from "./en.json";

const STORAGE_KEY = "rsod_lang";

function getStoredLang() {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored && ["zh", "en"].includes(stored)) {
    return stored;
  }
  const navigatorLang = navigator.language || navigator.userLanguage;
  if (navigatorLang.startsWith("zh")) {
    return "zh";
  }
  return "en";
}

const i18n = createI18n({
  legacy: false,
  locale: getStoredLang(),
  fallbackLocale: "zh",
  messages: {
    zh,
    en,
  },
});

export function setLanguage(lang) {
  if (["zh", "en"].includes(lang)) {
    i18n.global.locale.value = lang;
    localStorage.setItem(STORAGE_KEY, lang);
    window.location.reload();
  }
}

export function getCurrentLanguage() {
  return i18n.global.locale.value;
}

export default i18n;