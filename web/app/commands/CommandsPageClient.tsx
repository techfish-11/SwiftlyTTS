"use client";
import Link from "next/link";
import {
  ThemeProvider,
  CssBaseline,
  Container,
  Typography,
  Card,
  CardContent,
  Box,
  Button,
  Chip,
  Stack,
} from "@mui/material";
import theme from "../../lib/theme";

const commands = [
  {
    cmd: "/join",
    title: "ボイスチャンネル参加",
    usage: "/join",
    desc: "Botを自分が参加しているボイスチャンネルに呼びます。最初にこのコマンドを実行してください。",
    example: "/join",
  },
  {
    cmd: "/autojoin on /autojoin off",
    title: "自動参加設定",
    usage: "/autojoin on（VCに入った状態で実行） /autojoin off",
    desc: "指定したVCにメンバーが参加したときにBotが自動で参加するように設定します。onで現在のVCと読み上げチャンネルをDBに保存、offで無効化します（サーバーごとに1チャンネルまで）。",
    example: "/autojoin on",
  },
  {
    cmd: "/dictionary add",
    title: "辞書追加",
    usage: "/dictionary add 単語 よみかた user_dict:True",
    desc: "指定した単語の読み方をカスタマイズできます。サーバー辞書（デフォルト）またはユーザー辞書（ギルド横断）を選択可能。",
    example: "/dictionary add 甲斐田 かいだ user_dict:False",
  },
  {
    cmd: "/dictionary list",
    title: "辞書一覧",
    usage: "/dictionary list user_dict:True",
    desc: "サーバー辞書またはユーザー辞書の一覧を表示します。",
    example: "/dictionary list user_dict:False",
  },
  {
    cmd: "/dictionary remove",
    title: "辞書削除",
    usage: "/dictionary remove 単語 user_dict:True",
    desc: "指定した単語の読み方を削除します。サーバー辞書またはユーザー辞書から削除されます。",
    example: "/dictionary remove 甲斐田 user_dict:False",
  },
  {
    cmd: "/dictionary search",
    title: "辞書検索",
    usage: "/dictionary search 単語 user_dict:True",
    desc: "指定した単語の読み方を検索します。サーバー辞書またはユーザー辞書から検索されます。",
    example: "/dictionary search 甲斐田 user_dict:False",
  },
  {
    cmd: "/voice",
    title: "音声選択",
    usage: "/voice",
    desc: "自分の読み上げ音声を選択できます。コマンド実行後、番号を入力して話者を設定します。",
    example: "/voice",
  },
  {
    cmd: "/leave",
    title: "切断",
    usage: "/leave",
    desc: "Botをボイスチャンネルから退出させます。",
    example: "/leave",
  },
  {
    cmd: "/speed",
    title: "スピード調整",
    usage: "/speed [数値 or 空白]",
    desc: "サーバー全体の読み上げ速度を設定します。1.0～2.0の間で指定できます。resetでデフォルトに戻します。",
    example: "/speed 1.2",
  },
  {
    cmd: "/admin",
    title: "管理者コマンド（bot管理者専用）",
    usage: "/admin [コマンド]",
    desc: "管理者専用のコマンドを実行します。",
  },
  {
    cmd: "s",
    title: "読み上げキュー削除 & 読み上げ停止",
    usage: "s",
    desc: "sと読み上げチャンネルに送信すると、現在の読み上げキューを削除し、現在読み上げているメッセージの読み上げを停止します。スパムされた場合などに有効です。",
  },
];

export default function CommandsPageClient() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{ minHeight: "100vh", bgcolor: "background.default", py: { xs: 4, md: 8 } }}>
        <Container maxWidth="md">
          <Typography variant="h3" component="h1" fontWeight="bold" gutterBottom sx={{ textAlign: "center", mb: 3 }}>
            コマンド使用方法
          </Typography>
          <Typography variant="subtitle1" color="text.secondary" sx={{ textAlign: "center", mb: 5 }}>
            Swiftly読み上げbotで利用できる主なコマンドとその使い方をまとめました。
          </Typography>
          <Stack spacing={4}>
            {commands.map((c) => (
              <Card key={c.cmd} elevation={3} sx={{ borderRadius: 1, bgcolor: "background.paper", border: 1, borderColor: "outline.variant" }}>
                <CardContent>
                  <Box sx={{ display: "flex", alignItems: "center", gap: 2, mb: 1 }}>
                    <Chip label={c.cmd} color="primary" sx={{ fontFamily: 'Roboto Mono, monospace', fontWeight: 700, fontSize: 16, px: 1.5, py: 0.5 }} />
                    <Typography variant="h6" fontWeight="bold" sx={{ flex: 1 }}>{c.title}</Typography>
                  </Box>
                  <Typography color="text.secondary" sx={{ mb: 1 }}>{c.desc}</Typography>
                  <Box sx={{ display: "flex", alignItems: "center", mb: 0.5 }}>
                    <Typography variant="body2" color="text.secondary" sx={{ minWidth: 56 }}>使い方：</Typography>
                    <Box component="span" sx={{ fontFamily: 'Roboto Mono, monospace', bgcolor: "surface.variant", color: "onSurface.main", px: 1.5, py: 0.5, borderRadius: 1, fontSize: 15, ml: 1 }}>{c.usage}</Box>
                  </Box>
                  {c.example && (
                    <Box sx={{ display: "flex", alignItems: "center" }}>
                      <Typography variant="body2" color="text.secondary" sx={{ minWidth: 56 }}>例：</Typography>
                      <Box component="span" sx={{ fontFamily: 'Roboto Mono, monospace', bgcolor: "surface.main", color: "onSurface.variant", px: 1.5, py: 0.5, borderRadius: 1, fontSize: 15, ml: 1 }}>{c.example}</Box>
                    </Box>
                  )}
                </CardContent>
              </Card>
            ))}
          </Stack>
          <Box sx={{ display: "flex", justifyContent: "center", mt: 7 }}>
            <Button
              component={Link}
              href="/"
              variant="contained"
              color="primary"
              size="large"
              sx={{ borderRadius: 999, px: 5, py: 1.5, fontWeight: 700, boxShadow: 3 }}
            >
              ← トップページへ戻る
            </Button>
          </Box>
        </Container>
      </Box>
    </ThemeProvider>
  );
}