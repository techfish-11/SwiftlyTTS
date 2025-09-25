
import CommandsPageClient from "./CommandsPageClient";

export const metadata = {
  title: "コマンド一覧 | Swiftly読み上げbot",
  description: "Swiftly読み上げbotで利用できるコマンドの一覧です。",
};

export default function CommandsPage() {
  return <CommandsPageClient />;
}
