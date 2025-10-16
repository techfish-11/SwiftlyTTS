
import AuthClient from "./authclient";

export const metadata = {
  title: "ログイン | Swiftly読み上げbot",
  description: "Swiftly読み上げbotで利用できるコマンドの一覧です。",
};

export default function CommandsPage() {
  return <AuthClient />;
}
