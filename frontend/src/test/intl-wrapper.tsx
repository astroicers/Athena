import { NextIntlClientProvider } from "next-intl";
import messages from "../../messages/en.json";

export function IntlWrapper({ children }: { children: React.ReactNode }) {
  return (
    <NextIntlClientProvider locale="en" messages={messages}>
      {children}
    </NextIntlClientProvider>
  );
}
