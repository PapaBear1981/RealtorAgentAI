"use client";

import { useTranslation } from "react-i18next";
import { Button } from "./ui/button";

export function LanguageToggle() {
  const { i18n } = useTranslation();

  const toggle = () => {
    const newLang = i18n.language === "en" ? "vi" : "en";
    i18n.changeLanguage(newLang);
    if (typeof document !== "undefined") {
      document.documentElement.lang = newLang;
    }
  };

  return (
    <Button onClick={toggle} variant="outline" size="sm">
      {i18n.language === "en" ? "VI" : "EN"}
    </Button>
  );
}
