import { hasLocale } from "next-intl";
import { getRequestConfig } from "next-intl/server";
import { getDictionary } from "@/lib/i18n/dictionaries";
import { routing } from "./routing";

export default getRequestConfig(async ({ requestLocale }) => {
  const requested = await requestLocale;
  const locale = hasLocale(routing.locales, requested)
    ? requested
    : routing.defaultLocale;
  const { metadata, ...messages } = await getDictionary(locale);
  void metadata;

  return {
    locale,
    messages,
  };
});
