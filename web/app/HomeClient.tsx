"use client";
import React, { useEffect, useState } from 'react';
import {
  ThemeProvider,
  CssBaseline,
  Container,
  Box,
  Typography,
  Button,
  Card,
  CardContent,
  List,
  ListItem,
  ListItemText,
  Chip,
  Avatar,
  Dialog,
  DialogTitle,
  DialogContent,
  IconButton,
  Tooltip as MuiTooltip,
} from '@mui/material';
import {
  Cloud,
  FlashOn as Flash,
  MenuBook as BookOpen,
  Wifi,
  Refresh as RotateCcw,
  PlayArrow as Play,
  Settings,
  VolumeUp as Volume2,
  SkipPrevious as SkipBack,
  SkipNext as SkipForward,
  Add as Plus,
  Close as CloseIcon,
} from '@mui/icons-material';
import theme from '../lib/theme';
import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
  Legend,
} from 'chart.js';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend);

export default function Home() {
  const [serverCount, setServerCount] = useState<string>("Loading...");
  // Grafana モーダル制御
  const [grafanaOpen, setGrafanaOpen] = useState(false);

  const grafanaTarget = 'https://stats.sakana11.org/public-dashboards/68f9b3d55f43490c9d07c1daf1475f3c/';
  // we no longer embed Grafana iframe; use Prometheus querying instead
  
  type ChartDataType = {
    labels: string[];
    datasets: Array<{
      label: string;
      data: number[];
      fill?: boolean;
      borderColor: string;
      backgroundColor: string;
      tension?: number;
    }>;
  } | null;

  // Prometheus chart state
  const [promLoading, setPromLoading] = useState(false);
  const [promError, setPromError] = useState<string | null>(null);
  const [chartData, setChartData] = useState<ChartDataType>(null);

  async function fetchPrometheusSeries(promql = 'bot_server_count', rangeSeconds = 3600, step = 2419) {
    setPromLoading(true);
    setPromError(null);
    try {
      const end = Math.floor(Date.now() / 1000);
      const start = end - rangeSeconds;
      const url = `/api/prometheus/range?query=${encodeURIComponent(promql)}&start=${start}&end=${end}&step=${step}`;
      const res = await fetch(url);
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.error || `Status ${res.status}`);
      }
      const payload = await res.json();

      if (!payload || payload.status !== 'success' || !payload.data || !Array.isArray(payload.data.result)) {
        throw new Error('Unexpected Prometheus response');
      }

      const results: Array<{ metric: Record<string, string>; values: Array<[number | string, string]> }> = payload.data.result;
      if (results.length === 0) {
        // Empty result
        setChartData({ labels: [], datasets: [] });
        setPromLoading(false);
        return;
      }

      // Assume all series use the same timestamp steps. Use the first series to build labels.
      const firstValues: Array<[number | string, string]> = results[0].values;
      const labels = firstValues.map((v) => {
        const ts = typeof v[0] === 'string' ? Number(v[0]) : v[0];
        return new Date(ts * 1000).toLocaleTimeString();
      });

      const datasets = results.map((r, idx) => {
        const name = (r.metric && r.metric.__name__) || Object.values(r.metric).join(', ') || `series_${idx}`;
        const data = r.values.map((v) => parseFloat(String(v[1])));
        const hue = (idx * 70) % 360;
        return {
          label: name,
          data,
          fill: false,
          borderColor: `hsl(${hue} 80% 50%)`,
          backgroundColor: `hsl(${hue} 80% 40%)`,
          tension: 0.2,
        };
      });

      setChartData({ labels, datasets });
      setPromLoading(false);
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : String(e);
      setPromError(message);
      setPromLoading(false);
    }
  }

  useEffect(() => {
    fetch("/api/servercount")
      .then((res) => res.json())
      .then((data) => {
        if (typeof data.count === "number") {
          setServerCount(`${data.count}`);
        }
      })
      .catch(() => {
        // Fallback
      });
  }, []);

  useEffect(() => {
    if (grafanaOpen) {
      // Fetch 7 days of data at 1h resolution by default; query 'up' is generic and available in most Prometheus setups.
      fetchPrometheusSeries('bot_server_count', 604800, 3600);
    }
  }, [grafanaOpen]);

  const metrics = [
    // サーバーカードはクリックでGrafanaのパネルを開く
    { label: "サーバー", value: serverCount, icon: <Cloud />, onClick: () => setGrafanaOpen(true) },
    { label: "ボットレイテンシ", value: "~200ms", icon: <Flash /> },
    { label: "辞書", value: "∞", icon: <BookOpen /> },
  ];

  const features = [
    {
      title: "VOICEVOXエンジン",
      tag: "自然な音声合成",
      desc: "滑らかで自然な音声生成を実現するVOICEVOXを搭載。",
      icon: <Volume2 color="primary" />,
    },
    {
      title: "超高速パフォーマンス",
      tag: "専用GPU",
      desc: "GPUにより高速生成と低遅延を実現。",
      icon: <Flash color="secondary" />,
    },
    {
      title: "インテリジェント辞書",
      tag: "無制限登録",
      desc: "無制限なサーバーごとの辞書でカスタム発音を即時適用。",
      icon: <BookOpen color="primary" />,
    },
    {
      title: "ユーザー辞書",
      tag: "ギルド横断",
      desc: "ギルドをまたいで使える個人辞書。登録したユーザーのみ適用。",
      icon: <BookOpen color="secondary" />,
    },
    {
      title: "高速ネットワーク",
      tag: "超低遅延",
      desc: "200ms未満の応答時間を目指す高速ネットワーク。",
      icon: <Wifi color="info" />,
    },
    {
      title: "自動復帰",
      tag: "自動回復",
      desc: "ボット再起動後に自動で前のボイスチャンネルに再参加。",
      icon: <RotateCcw color="success" />,
    },
  ];

  const commands = [
    { cmd: "/join", title: "ボイスチャンネル参加", desc: "1つのコマンドで即時開始", icon: <Play /> },
    { cmd: "/dictionary", title: "辞書機能", desc: "カスタム発音を登録", icon: <BookOpen /> },
    { cmd: "/voice", title: "音声選択", desc: "設定をパーソナライズ", icon: <Settings /> },
    { cmd: "/leave", title: "切断", desc: "ボイスチャンネルから退出", icon: <SkipBack /> },
    { cmd: "/speed", title: "速度調整", desc: "話す速度を設定", icon: <SkipForward /> },
  ];

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{ backgroundColor: 'background.default', minHeight: '100vh' }}>
        {/* Header */}
        <Container maxWidth="lg" sx={{ pt: 8, pb: 4 }}>
          <Box sx={{ textAlign: 'center', mb: 6 }}>
            <Avatar sx={{ mx: 'auto', mb: 2, bgcolor: 'primary.main', width: 64, height: 64 }}>
              <Cloud sx={{ fontSize: 32 }} />
            </Avatar>

            <Typography variant="overline" sx={{ color: 'onSurface.variant', letterSpacing: 2 }}>
              超低遅延音声ボット
            </Typography>
            {/* GitHubバッジ */}
            <Box sx={{ display: 'flex', justifyContent: 'center', gap: 1, mb: 1, mt: 2 }}>
              <a
                href="https://github.com/techfish-11/SwiftlyTTS"
                target="_blank"
                rel="noopener noreferrer"
                style={{ display: 'inline-block' }}
              >
                <img
                  src="https://img.shields.io/github/stars/techfish-11/swiftlytts?style=flat-square"
                  alt="GitHub stars"
                  height={28}
                  style={{ verticalAlign: 'middle' }}
                />
              </a>
              <a
                href="https://github.com/techfish-11/SwiftlyTTS/network/members"
                target="_blank"
                rel="noopener noreferrer"
                style={{ display: 'inline-block' }}
              >
                <img
                  src="https://img.shields.io/github/forks/techfish-11/SwiftlyTTS?style=flat-square"
                  alt="GitHub forks"
                  height={28}
                  style={{ verticalAlign: 'middle' }}
                />
              </a>
              <a
                href="https://github.com/techfish-11/SwiftlyTTS"
                target="_blank"
                rel="noopener noreferrer"
                style={{ display: 'inline-block' }}
              >
                <img
                  src="https://img.shields.io/github/languages/top/techfish-11/SwiftlyTTS?style=flat-square"
                  alt="GitHub license"
                  height={28}
                  style={{ verticalAlign: 'middle' }}
                />
               </a>
              <a
                href="https://github.com/techfish-11/SwiftlyTTS"
                target="_blank"
                rel="noopener noreferrer"
                style={{ display: 'inline-block' }}
              >
                <img
                  src="https://img.shields.io/github/contributors/techfish-11/swiftlytts"
                  alt="GitHub license"
                  height={28}
                  style={{ verticalAlign: 'middle' }}
                />
               </a>

              <a
                href="https://github.com/techfish-11/SwiftlyTTS"
                target="_blank"
                rel="noopener noreferrer"
                style={{ display: 'inline-block' }}
              >
                <img
                  src="https://img.shields.io/github/license/techfish-11/SwiftlyTTS"
                  alt="GitHub license"
                  height={28}
                  style={{ verticalAlign: 'middle' }}
                />
               </a>

            </Box>

            <Typography variant="h1" sx={{ mt: 2, mb: 3, fontWeight: 300 }}>
              SwiftlyTTS
            </Typography>

            <Typography variant="h5" sx={{ mb: 4, color: 'onSurface.variant', maxWidth: 600, mx: 'auto' }}>
              VOICEVOX搭載の高速・設定不要テキスト読み上げボット。設定は一切不要です。
            </Typography>
            <Box sx={{ display: 'flex', gap: 2, justifyContent: 'center', flexWrap: 'wrap' }}>
              <Button
                variant="contained"
                size="large"
                href="https://discord.com/oauth2/authorize?client_id=1371465579780767824"
                sx={{
                  px: 4,
                  py: 1.5,
                  fontSize: '1.1rem',
                  borderRadius: -10,
                  textTransform: 'none',
                }}
              >
                Discordに追加
              </Button>
              <Button
                variant="outlined"
                size="large"
                href="/commands"
                sx={{
                  px: 4,
                  py: 1.5,
                  borderRadius: -10,
                  textTransform: 'none',
                }}
              >
                コマンド一覧
              </Button>
              <Button
                variant="outlined"
                size="large"
                href="/auth/signin"
                sx={{
                  px: 4,
                  py: 1.5,
                  borderRadius: -10,
                  textTransform: 'none',
                }}
              >
                Webダッシュボードログイン
              </Button>

            </Box>
          </Box>

          {/* Metrics */}
          <Box sx={{ display: 'flex', gap: 3, flexWrap: 'wrap', justifyContent: 'center' }}>
            {metrics.map((m) => (
              m.label === "サーバー" ? (
                <MuiTooltip title="クリックするとグラフが見れます" key={m.label}>
                  <Card
                    sx={{ borderRadius: 1, boxShadow: 1, minWidth: 120, flex: 1, maxWidth: 200, cursor: m.onClick ? 'pointer' : 'default' }}
                    onClick={m.onClick}
                    role={m.onClick ? 'button' : undefined}
                    aria-label={m.onClick ? `Open ${m.label} Grafana panel` : undefined}
                  >
                     <CardContent sx={{ textAlign: 'center', py: 3 }}>
                       <Box sx={{ color: 'primary.main', mb: 1 }}>{m.icon}</Box>
                       <Typography variant="h3" sx={{ fontWeight: 600, mb: 1 }}>
                         {m.value}
                       </Typography>
                       <Typography variant="caption" sx={{ color: 'onSurface.variant', textTransform: 'uppercase', letterSpacing: 1 }}>
                         {m.label}
                       </Typography>
                     </CardContent>
                   </Card>
                </MuiTooltip>
              ) : (
                <Card
                  sx={{ borderRadius: 1, boxShadow: 1, minWidth: 120, flex: 1, maxWidth: 200, cursor: m.onClick ? 'pointer' : 'default' }}
                  key={m.label}
                  onClick={m.onClick}
                  role={m.onClick ? 'button' : undefined}
                  aria-label={m.onClick ? `Open ${m.label} Grafana panel` : undefined}
                >
                   <CardContent sx={{ textAlign: 'center', py: 3 }}>
                     <Box sx={{ color: 'primary.main', mb: 1 }}>{m.icon}</Box>
                     <Typography variant="h3" sx={{ fontWeight: 600, mb: 1 }}>
                       {m.value}
                     </Typography>
                     <Typography variant="caption" sx={{ color: 'onSurface.variant', textTransform: 'uppercase', letterSpacing: 1 }}>
                       {m.label}
                     </Typography>
                   </CardContent>
                 </Card>
              )
            ))}
          </Box>
          {/* Grafana パネルモーダル */}
          <Dialog
            open={grafanaOpen}
            onClose={() => setGrafanaOpen(false)}
            fullWidth
            maxWidth="lg"
            aria-labelledby="grafana-dialog-title"
          >
            <DialogTitle id="grafana-dialog-title" sx={{ pr: 5 }}>
              サーバー数グラフ
              <IconButton
                aria-label="close"
                onClick={() => setGrafanaOpen(false)}
                sx={{ position: 'absolute', right: 8, top: 8 }}
              >
                <CloseIcon />
              </IconButton>
            </DialogTitle>
            <DialogContent dividers sx={{ p: 3 }}>
              {promLoading && (
                <Box sx={{ height: 320, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>読み込み中…</Box>
              )}
              {promError && (
                <Box sx={{ p: 3, color: 'error.main' }}>プロメテウスからデータを取得できませんでした: {promError}</Box>
              )}
              {!promLoading && !promError && chartData && (
                <Box sx={{ width: '100%', height: 420 }}>
                  <Line
                    data={chartData}
                    options={{
                      responsive: true,
                      maintainAspectRatio: false,
                      plugins: { legend: { position: 'bottom' } },
                      scales: { x: { display: true }, y: { display: true } },
                    }}
                  />
                </Box>
              )}
              {/* フォールバック: 元の Grafana を別タブで開くリンク */}
              <Box sx={{ mt: 2, textAlign: 'right' }}>
                <Button size="small" href={grafanaTarget} target="_blank" rel="noopener noreferrer">
                  更に詳しく見る (Grafanaに移動します)
                </Button>
              </Box>
            </DialogContent>
          </Dialog>
        </Container>

        {/* Features */}
        <Box id="features" sx={{ backgroundColor: 'surface.variant', py: 8 }}>
          <Container maxWidth="lg">
            <Typography variant="h2" sx={{ textAlign: 'center', mb: 2, fontWeight: 300 }}>
              なぜSwiftly読み上げなのか？
            </Typography>
            <Typography variant="body1" sx={{ textAlign: 'center', mb: 6, color: 'onSurface.variant', maxWidth: 600, mx: 'auto' }}>
              高性能CPUとGPUにより応答時間を最小化。無制限な辞書システムと夜間でも高速な読み上げを提供します。
            </Typography>
            <Box sx={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
              {features.map((f) => (
                <Card sx={{ height: '100%', borderRadius: 1, boxShadow: 1, flex: '1 1 300px', minWidth: 250 }} key={f.title}>
                  <CardContent sx={{ p: 3 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                      {f.icon}
                      <Box sx={{ ml: 2 }}>
                        <Typography variant="h6" sx={{ fontWeight: 500 }}>
                          {f.title}
                        </Typography>
                        <Chip label={f.tag} size="small" variant="outlined" sx={{ mt: 0.5 }} />
                      </Box>
                    </Box>
                    <Typography variant="body2" sx={{ color: 'onSurface.variant' }}>
                      {f.desc}
                    </Typography>
                  </CardContent>
                </Card>
              ))}
            </Box>
          </Container>
        </Box>

        {/* Commands */}
        <Container id="commands" maxWidth="lg" sx={{ py: 8 }}>
          <Box sx={{ display: 'flex', gap: 6, flexDirection: { xs: 'column', md: 'row' } }}>
            <Box sx={{ flex: 1 }}>
              <Typography variant="h2" sx={{ mb: 3, fontWeight: 300 }}>
                シンプルなコマンド
              </Typography>
              <Typography variant="body1" sx={{ mb: 4, color: 'onSurface.variant' }}>
                セットアップ不要。直感的なスラッシュコマンドで最初から自然なTTSを提供。
              </Typography>
              <Card sx={{ borderRadius: 3, boxShadow: 1 }}>
                <List sx={{ py: 2 }}>
                  {commands.map((c) => (
                    <ListItem key={c.cmd} sx={{ px: 3 }}>
                      <Box sx={{ mr: 2, color: 'primary.main' }}>{c.icon}</Box>
                      <ListItemText
                        primary={
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                            <Typography variant="body2" sx={{ fontFamily: 'monospace', bgcolor: 'surface.variant', px: 1, py: 0.5, borderRadius: 1 }}>
                              {c.cmd}
                            </Typography>
                            <Typography variant="subtitle1">{c.title}</Typography>
                          </Box>
                        }
                        secondary={c.desc}
                      />
                    </ListItem>
                  ))}
                </List>
              </Card>
            </Box>
            <Box sx={{ flex: 1 }}>
              <Card sx={{ height: '100%', borderRadius: 3, boxShadow: 1, p: 3 }}>
                <Typography variant="h5" sx={{ mb: 2 }}>
                  Swiftlyの考え
                </Typography>
                <Typography variant="body2" sx={{ color: 'onSurface.variant', mb: 3 }}>
                  Swiftlyは超低遅延と高可用性を最優先に設計されています。ユーザー体験を損なわないために、これらの原則を守っています：
                </Typography>
                <Box component="ul" sx={{ pl: 3, m: 0 }}>
                  <Typography component="li" variant="body2" sx={{ mb: 1, color: 'onSurface.variant' }}>
                    不要な機能を排除
                  </Typography>
                  <Typography component="li" variant="body2" sx={{ mb: 1, color: 'onSurface.variant' }}>
                    不要な応答メッセージを排除
                  </Typography>
                  <Typography component="li" variant="body2" sx={{ mb: 1, color: 'onSurface.variant' }}>
                    必要なメトリクスのみを可視化
                  </Typography>
                  <Typography component="li" variant="body2" sx={{ color: 'onSurface.variant' }}>
                    ユーザーが貢献できるようにする（オープンソース）
                  </Typography>
                </Box>
                <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
                  <img
                    src="/botsyoukai.gif"
                    alt="SwiftlyTTS Bot紹介"
                    style={{ maxWidth: '100%', height: 'auto', borderRadius: 8, boxShadow: '0 2px 8px rgba(0,0,0,0.08)' }}
                  />
                </Box>
              </Card>
            </Box>
          </Box>
        </Container>

        {/* CTA Section */}
        <Box sx={{ backgroundColor: 'primary.main', color: 'primary.contrastText', py: 8 }}>
          <Container maxWidth="lg">
            <Box sx={{ display: 'flex', gap: 6, flexDirection: { xs: 'column', md: 'row' }, alignItems: 'center' }}>
              <Box sx={{ flex: 2 }}>
                <Typography variant="h2" sx={{ mb: 3, fontWeight: 300 }}>
                  サーバーに追加して開始
                </Typography>
                <Typography variant="h6" sx={{ mb: 4, opacity: 0.9 }}>
                  セットアップは0秒で完了。サーバー管理権限のみ必要 - ボット権限は管理者権限不要。コミュニティに高速で安定したTTSを提供。
                </Typography>
                <Box sx={{ display: 'flex', gap: 3, flexWrap: 'wrap' }}>
                  <Button
                    variant="contained"
                    size="large"
                    href="https://discord.com/oauth2/authorize?client_id=1371465579780767824"
                    sx={{
                      bgcolor: 'common.white',
                      color: 'primary.main',
                      px: 4,
                      py: 1.5,
                      borderRadius: 28,
                      textTransform: 'none',
                      fontSize: '1.1rem',
                      '&:hover': { bgcolor: 'grey.100' }
                    }}
                  >
                    今すぐサーバーに追加
                  </Button>
                  <Button
                    variant="outlined"
                    size="large"
                    href="/commands"
                    sx={{
                      borderColor: 'common.white',
                      color: 'common.white',
                      px: 4,
                      py: 1.5,
                      borderRadius: 28,
                      textTransform: 'none',
                      '&:hover': { borderColor: 'grey.300', bgcolor: 'rgba(255,255,255,0.1)' }
                    }}
                  >
                    コマンドを表示
                  </Button>
                </Box>
              </Box>
              <Box sx={{ flex: 1, width: '100%', maxWidth: 400 }}>
                <Card sx={{ borderRadius: 3, boxShadow: 2, bgcolor: 'background.paper' }}>
                  <CardContent sx={{ p: 3 }}>
                    <Typography variant="h6" sx={{ mb: 2 }}>
                      開始する
                    </Typography>
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                        <Plus sx={{ color: 'success.main' }} />
                        <Typography variant="body2">完全無料</Typography>
                      </Box>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                        <Flash sx={{ color: 'warning.main' }} />
                        <Typography variant="body2">セットアップ時間: 0秒</Typography>
                      </Box>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                        <Cloud sx={{ color: 'info.main' }} />
                        <Typography variant="body2">24/7目標稼働時間</Typography>
                      </Box>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                        <BookOpen sx={{ color: 'secondary.main' }} />
                        <Typography variant="body2">無制限辞書</Typography>
                      </Box>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                        <Wifi sx={{ color: 'primary.main' }} />
                        <Typography variant="body2">超低遅延 ~200ms</Typography>
                      </Box>
                    </Box>
                    <Button
                      fullWidth
                      variant="contained"
                      href="https://discord.com/oauth2/authorize?client_id=1371465579780767824"
                      sx={{ mt: 3, borderRadius: 28, textTransform: 'none' }}
                    >
                      今すぐ追加
                    </Button>
                    <Typography variant="caption" sx={{ display: 'block', mt: 2, color: 'text.secondary', textAlign: 'center' }}>
                      サーバー管理権限が必要です。ボットは権限を必要としません。
                    </Typography>
                  </CardContent>
                </Card>
              </Box>
            </Box>
          </Container>
        </Box>

        {/* フッター */}
        <Box sx={{ bgcolor: 'background.paper', py: 6, borderTop: 1, borderColor: 'outline.variant' }}>
          <Container maxWidth="lg">
            <Box sx={{ borderBottom: 1, borderColor: 'outline.variant', pb: 3, mb: 3 }}>
              <Typography variant="caption" sx={{ display: 'block', mb: 2, color: 'onSurface.variant' }}>
          ※1 ボットレイテンシは状況により200msを超える場合があります。ネットワークや負荷の影響を受けます。
              </Typography>
              <Typography variant="caption" sx={{ display: 'block', mb: 2, color: 'onSurface.variant' }}>
          ※2 辞書登録は無制限ですが、サーバーのストレージ容量に依存します。
              </Typography>
              <Typography variant="caption" sx={{ display: 'block', mb: 2, color: 'onSurface.variant' }}>
          ※3 インストール後はボイスチャンネルに参加するだけですぐに利用できます。
              </Typography>
              <Typography variant="caption" sx={{ display: 'block', color: 'onSurface.variant' }}>
          ※4 24時間365日の稼働を目指していますが、保証はできません。
              </Typography>
            </Box>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 2 }}>
              <Typography variant="body2" sx={{ fontWeight: 500 }}>
                &copy; 2025 Swiftly読み上げbot All Rights Reserved.
              </Typography>
              <Box sx={{ display: 'flex', gap: 3 }}>
                <Button variant="text" component="a" href="#features" sx={{ color: 'primary.main', textTransform: 'none', p: 0, minWidth: 'auto' }}>
                  特長
                </Button>
                <Button variant="text" component="a" href="/commands" sx={{ color: 'primary.main', textTransform: 'none', p: 0, minWidth: 'auto' }}>
                  コマンド
                </Button>
                <Button variant="text" component="a" href="https://discord.com/oauth2/authorize?client_id=1371465579780767824" sx={{ color: 'primary.main', textTransform: 'none', p: 0, minWidth: 'auto' }}>
                  サーバーに追加
                </Button>
                <Button variant="text" component="a" href="https://github.com/techfish-11/SwiftlyTTS" sx={{ color: 'primary.main', textTransform: 'none', p: 0, minWidth: 'auto' }}>
                  GitHub
                </Button>

              </Box>
            </Box>
          </Container>
        </Box>
            </Box>
          </ThemeProvider>
        );
      }
