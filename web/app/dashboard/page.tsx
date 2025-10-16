
import DashboardClient from "./DashboardClient";

export const metadata = {
  title: "ダッシュボード | Swiftly読み上げbot",
  description: "Swiftly読み上げbotで利用できるコマンドの一覧です。",
};

export default function CommandsPage() {
  return <DashboardClient />;
}
