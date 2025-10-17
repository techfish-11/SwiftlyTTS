"use client";

import React, { useEffect, useState } from "react";
import { useSession, signOut } from "next-auth/react";
import { useRouter } from "next/navigation";
import Box from "@mui/material/Box";
import Container from "@mui/material/Container";
import Avatar from "@mui/material/Avatar";
import Typography from "@mui/material/Typography";
import Button from "@mui/material/Button";
import Paper from "@mui/material/Paper";
import AppBar from "@mui/material/AppBar";
import Toolbar from "@mui/material/Toolbar";
import IconButton from "@mui/material/IconButton";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableContainer from "@mui/material/TableContainer";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import TextField from "@mui/material/TextField";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Divider from "@mui/material/Divider";
import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";
import Chip from "@mui/material/Chip";

type UserDictionaryEntry = { key: string; value: string };
type Guild = { id: string; name: string };

export default function DashboardClient() {
  const { data: session, status } = useSession();
  const router = useRouter();

  // サーバー数表示用state
  const [serverCount, setServerCount] = useState<string>("...");

  // ユーザー辞書管理用state
  // ギルド辞書管理用state
  const [guilds, setGuilds] = useState<Guild[]>([]);
  const [guildsLoading, setGuildsLoading] = useState(false);
  const [guildsError, setGuildsError] = useState<string|null>(null);
  const [guildsPolling, setGuildsPolling] = useState(false);
  const [selectedGuild, setSelectedGuild] = useState<string>("");
  const [guildDictionary, setGuildDictionary] = useState<UserDictionaryEntry[]>([]);
  const [guildDictKey, setGuildDictKey] = useState("");
  const [guildDictValue, setGuildDictValue] = useState("");
  const [guildDictEditKey, setGuildDictEditKey] = useState<string|null>(null);
  const [guildDictEditValue, setGuildDictEditValue] = useState("");
  const [guildDictLoading, setGuildDictLoading] = useState(false);
  const [guildDictError, setGuildDictError] = useState<string|null>(null);
  // ユーザーの所属ギルド一覧取得（ポーリング対応）
  const fetchGuilds = React.useCallback(async (force?: boolean) => {
    setGuildsLoading(true);
    setGuildsError(null);
    setGuildsPolling(false);
    try {
      const url = force ? "/api/servers?force=1" : "/api/servers";
      const res = await fetch(url, { credentials: "include" }); // ← 追加
      const data = await res.json();
      if (res.ok && data.servers) {
        setGuilds(data.servers || []);
        // サーバー選択時に再取得しないようにselectedGuild依存を外す
        // if (data.servers && data.servers.length > 0 && !selectedGuild) {
        //   setSelectedGuild(data.servers[0].id);
        // }
        // サーバー選択は初回のみ自動選択
        setSelectedGuild(prev => prev || (data.servers && data.servers.length > 0 ? data.servers[0].id : ""));
      } else if (data.status === "pending" && data.job_id) {
        // ポーリング開始
        setGuildsPolling(true);
        let tries = 0;
        const poll = async () => {
          tries++;
          const pollRes = await fetch(`/api/servers?job_id=${data.job_id}`, { credentials: "include" }); // ← 追加
          const pollData = await pollRes.json();
          if (pollData.status === "done" && pollData.servers) {
            setGuilds(pollData.servers || []);
            setGuildsPolling(false);
            setSelectedGuild(prev => prev || (pollData.servers && pollData.servers.length > 0 ? pollData.servers[0].id : ""));
          } else if (pollData.status === "error") {
            setGuilds([]);
            setGuildsError(pollData.error || "サーバー一覧の取得に失敗しました");
            setGuildsPolling(false);
          } else if (tries < 20) {
            setTimeout(poll, 1000);
          } else {
            setGuilds([]);
            setGuildsError("サーバー一覧の取得にタイムアウトしました");
            setGuildsPolling(false);
          }
        };
        poll();
      } else {
        setGuilds([]);
        setGuildsError(data.error || "サーバー一覧の取得に失敗しました");
      }
    } catch {
      setGuilds([]);
      setGuildsError("サーバー一覧の取得に失敗しました");
    } finally {
      setGuildsLoading(false);
    }
  }, []); // ← selectedGuildを依存配列から除外

  // 選択ギルドの辞書取得
  const fetchGuildDictionary = async (guildId: string) => {
    setGuildDictLoading(true);
    setGuildDictError(null);
    try {
      const res = await fetch(`/api/guild-dictionary?guild_id=${guildId}`);
      const data = await res.json();
      setGuildDictionary(data.dictionary || []);
    } catch {
      setGuildDictError("ギルド辞書の取得に失敗しました");
    } finally {
      setGuildDictLoading(false);
    }
  };
  const [userDictionary, setUserDictionary] = useState<UserDictionaryEntry[]>([]);
  const [dictKey, setDictKey] = useState("");
  const [dictValue, setDictValue] = useState("");
  const [dictEditKey, setDictEditKey] = useState<string|null>(null);
  const [dictEditValue, setDictEditValue] = useState("");
  const [dictLoading, setDictLoading] = useState(false);
  const [dictError, setDictError] = useState<string|null>(null);
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);

  // ユーザー辞書取得
  const fetchUserDictionary = async () => {
    setDictLoading(true);
    setDictError(null);
    try {
      const res = await fetch("/api/user-dictionary");
      const data = await res.json();
      setUserDictionary(data.dictionary || []);
    } catch {
      setDictError("ユーザー辞書の取得に失敗しました");
    } finally {
      setDictLoading(false);
    }
  };

  useEffect(() => {
    if (status === "unauthenticated") {
      router.replace("/auth/signin");
    }
  }, [status, router]);

  useEffect(() => {
    if (status === "authenticated") {
      fetchUserDictionary();
      fetchGuilds();
      // サーバー数取得
      fetch("/api/servercount", { credentials: "include" })
        .then((res) => res.json())
        .then((data) => {
          if (typeof data.count === "number") {
            setServerCount(`${data.count}`);
          }
        })
        .catch(() => {
          setServerCount("N/A");
        });
    }
  }, [status, fetchGuilds]);

  // ギルド選択時に辞書取得のみ
  useEffect(() => {
    if (selectedGuild) {
      fetchGuildDictionary(selectedGuild);
    }
  }, [selectedGuild]);
  // ギルド辞書エントリ追加
  const handleAddGuildDictionary = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!guildDictKey || !guildDictValue || !selectedGuild) return;
    setGuildDictLoading(true);
    setGuildDictError(null);
    try {
      const res = await fetch("/api/guild-dictionary", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ guild_id: selectedGuild, key: guildDictKey, value: guildDictValue }),
      });
      if (!res.ok) throw new Error();
      setGuildDictKey("");
      setGuildDictValue("");
      fetchGuildDictionary(selectedGuild);
    } catch {
      setGuildDictError("追加に失敗しました");
    } finally {
      setGuildDictLoading(false);
    }
  };

  // ギルド辞書エントリ編集開始
  const handleEditGuildStart = (key: string, value: string) => {
    setGuildDictEditKey(key);
    setGuildDictEditValue(value);
  };

  // ギルド辞書エントリ編集保存
  const handleEditGuildSave = async () => {
    if (!guildDictEditKey || !selectedGuild) return;
    setGuildDictLoading(true);
    setGuildDictError(null);
    try {
      const res = await fetch("/api/guild-dictionary", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ guild_id: selectedGuild, key: guildDictEditKey, value: guildDictEditValue }),
      });
      if (!res.ok) throw new Error();
      setGuildDictEditKey(null);
      setGuildDictEditValue("");
      fetchGuildDictionary(selectedGuild);
    } catch {
      setGuildDictError("編集に失敗しました");
    } finally {
      setGuildDictLoading(false);
    }
  };

  // ギルド辞書エントリ削除
  const handleDeleteGuildDictionary = async (key: string) => {
    if (!window.confirm("本当に削除しますか？")) return;
    setGuildDictLoading(true);
    setGuildDictError(null);
    try {
      const res = await fetch("/api/guild-dictionary", {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ guild_id: selectedGuild, key }),
      });
      if (!res.ok) throw new Error();
      fetchGuildDictionary(selectedGuild);
    } catch {
      setGuildDictError("削除に失敗しました");
    } finally {
      setGuildDictLoading(false);
    }
  };

  // 辞書エントリ追加
  const handleAddDictionary = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!dictKey || !dictValue) return;
    setDictLoading(true);
    setDictError(null);
    try {
      const res = await fetch("/api/user-dictionary", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ key: dictKey, value: dictValue }),
      });
      if (!res.ok) throw new Error();
      setDictKey("");
      setDictValue("");
      fetchUserDictionary();
    } catch {
      setDictError("追加に失敗しました");
    } finally {
      setDictLoading(false);
    }
  };

  // 辞書エントリ編集開始
  const handleEditStart = (key: string, value: string) => {
    setDictEditKey(key);
    setDictEditValue(value);
  };

  // 辞書エントリ編集保存
  const handleEditSave = async () => {
    if (!dictEditKey) return;
    setDictLoading(true);
    setDictError(null);
    try {
      const res = await fetch("/api/user-dictionary", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ key: dictEditKey, value: dictEditValue }),
      });
      if (!res.ok) throw new Error();
      setDictEditKey(null);
      setDictEditValue("");
      fetchUserDictionary();
    } catch {
      setDictError("編集に失敗しました");
    } finally {
      setDictLoading(false);
    }
  };

  // 辞書エントリ削除
  const handleDeleteDictionary = async (key: string) => {
    if (!window.confirm("本当に削除しますか？")) return;
    setDictLoading(true);
    setDictError(null);
    try {
      const res = await fetch("/api/user-dictionary", {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ key }),
      });
      if (!res.ok) throw new Error();
      fetchUserDictionary();
    } catch {
      setDictError("削除に失敗しました");
    } finally {
      setDictLoading(false);
    }
  };

  const open = Boolean(anchorEl);

  const handleMenu = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const handleSignOut = () => {
    handleClose();
    signOut({ callbackUrl: "/" });
  };

  if (status === "loading") {
    return (
      <Container sx={{ py: 8 }}>
        <Typography>読み込み中…</Typography>
      </Container>
    );
  }

  if (!session) {
    // 状態が unauthenticated にリダイレクト済みなので何も出さない
    return null;
  }

  const user = session.user;

  return (
    <Box sx={{ minHeight: "100vh", bgcolor: "#fafafa" }}>
      {/* ヘッダーバー */}
      <AppBar position="static" elevation={0} sx={{ bgcolor: "white", borderBottom: 1, borderColor: "divider" }}>
        <Toolbar>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1, color: "text.primary", fontWeight: 500 }}>
            Swiftly読み上げbot ダッシュボード
          </Typography>
          {/* サーバー数表示 */}
          <Chip
            label={`${serverCount} サーバー`}
            size="small"
            sx={{
              mr: 2,
              bgcolor: "#e8f5e9",
              color: "#2e7d32",
              fontWeight: 500,
              fontSize: "0.813rem",
              height: 28,
              "& .MuiChip-label": {
                px: 1.5,
              },
            }}
          />
          <IconButton onClick={handleMenu} sx={{ p: 0 }}>
            <Avatar src={user?.image ?? undefined} alt={user?.name ?? "user"} sx={{ width: 32, height: 32 }}>
              {user?.name ? user.name.charAt(0).toUpperCase() : "U"}
            </Avatar>
          </IconButton>
          <Menu
            anchorEl={anchorEl}
            open={open}
            onClose={handleClose}
            anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
            transformOrigin={{ vertical: "top", horizontal: "right" }}
          >
            <Box sx={{ px: 2, py: 1.5, minWidth: 200 }}>
              <Typography variant="body2" fontWeight={600}>{user?.name ?? "ユーザー"}</Typography>
            </Box>
            <Divider />
            <MenuItem onClick={handleSignOut}>サインアウト</MenuItem>
          </Menu>
        </Toolbar>
      </AppBar>

      {/* メインコンテンツ */}
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Box sx={{ mb: 4 }}>
          <Typography variant="h4" sx={{ fontWeight: 400, color: "text.primary", mb: 0.5 }}>
            ダッシュボード
          </Typography>
          <Typography variant="body2" color="text.secondary">
            辞書の管理やBOT設定を行います
          </Typography>
        </Box>

        {/* ウェルカムカード */}
        <Card elevation={0} sx={{ mb: 3, border: 1, borderColor: "divider" }}>
          <CardContent sx={{ p: 3 }}>
            <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
              <Avatar src={user?.image ?? undefined} alt={user?.name ?? "user"} sx={{ width: 56, height: 56 }}>
                {user?.name ? user.name.charAt(0).toUpperCase() : "U"}
              </Avatar>
              <Box>
                <Typography variant="h6" sx={{ fontWeight: 500 }}>
                  ようこそ、{user?.name ?? "ゲスト"} さん
                </Typography>
                <Chip label="ログイン済み" size="small" sx={{ mt: 0.5, bgcolor: "#e8f5e9", color: "#2e7d32", fontWeight: 500 }} />
              </Box>
            </Box>
          </CardContent>
        </Card>

        {/* ギルド辞書管理カード */}
        <Card elevation={0} sx={{ border: 1, borderColor: "divider", mb: 4 }}>
          <CardContent sx={{ p: 3 }}>
            <Typography variant="h6" sx={{ fontWeight: 500, mb: 0.5 }}>
              ギルド辞書
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
              参加しているサーバーの辞書を管理します
            </Typography>

            {/* ギルド選択・ローディング・エラー表示 */}
            <Box sx={{ mb: 2, display: "flex", alignItems: "center", gap: 2 }}>
              {guildsLoading || guildsPolling ? (
                <Typography sx={{ py: 2 }}>
                  {guildsPolling ? "サーバー一覧取得中…（Discord APIから取得しています）" : "サーバー一覧取得中…"}
                </Typography>
              ) : guildsError ? (
                <Paper elevation={0} sx={{ p: 2, mb: 2, bgcolor: "#fdecea", border: 1, borderColor: "#f5c6cb" }}>
                  <Typography variant="body2" color="error">{guildsError}</Typography>
                </Paper>
              ) : (
                <TextField
                  select
                  label="サーバー選択"
                  value={selectedGuild}
                  onChange={e => setSelectedGuild(e.target.value)}
                  size="small"
                  sx={{ minWidth: 240, bgcolor: "white" }}
                  disabled={guilds.length === 0}
                >
                  {guilds.map(g => (
                    <MenuItem key={g.id} value={g.id}>{g.name}</MenuItem>
                  ))}
                </TextField>
              )}
              <Button
                variant="outlined"
                size="small"
                sx={{ ml: 1, minWidth: 120 }}
                onClick={() => fetchGuilds(true)}
                disabled={guildsLoading || guildsPolling}
              >
                ギルドキャッシュ再読み込み
              </Button>
            </Box>

            {guildDictError && (
              <Paper elevation={0} sx={{ p: 2, mb: 2, bgcolor: "#fdecea", border: 1, borderColor: "#f5c6cb" }}>
                <Typography variant="body2" color="error">{guildDictError}</Typography>
              </Paper>
            )}

            {/* 追加フォーム */}
            <Paper elevation={0} sx={{ p: 2, mb: 3, bgcolor: "#f5f5f5" }}>
              <form onSubmit={handleAddGuildDictionary}>
                <Box sx={{ display: "flex", gap: 2, alignItems: "flex-start" }}>
                  <TextField
                    size="small"
                    label="キー"
                    value={guildDictKey}
                    onChange={e => setGuildDictKey(e.target.value)}
                    disabled={guildDictLoading || !selectedGuild}
                    sx={{ width: 200, bgcolor: "white" }}
                  />
                  <TextField
                    size="small"
                    label="値（読み方）"
                    value={guildDictValue}
                    onChange={e => setGuildDictValue(e.target.value)}
                    disabled={guildDictLoading || !selectedGuild}
                    sx={{ width: 280, bgcolor: "white" }}
                  />
                  <Button
                    type="submit"
                    variant="contained"
                    disabled={guildDictLoading || !guildDictKey || !guildDictValue || !selectedGuild}
                    sx={{
                      bgcolor: "#1976d2",
                      textTransform: "none",
                      boxShadow: "none",
                      "&:hover": { boxShadow: 1 }
                    }}
                  >
                    追加
                  </Button>
                </Box>
              </form>
            </Paper>

            {/* 辞書テーブル */}
            {guildDictLoading ? (
              <Typography>読み込み中…</Typography>
            ) : guildDictionary.length === 0 ? (
              <Box sx={{ textAlign: "center", py: 4 }}>
                <Typography variant="body2" color="text.secondary">
                  辞書エントリがありません。上のフォームから追加してください。
                </Typography>
              </Box>
            ) : (
              <TableContainer>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell sx={{ fontWeight: 600, color: "text.secondary", fontSize: "0.875rem" }}>キー</TableCell>
                      <TableCell sx={{ fontWeight: 600, color: "text.secondary", fontSize: "0.875rem" }}>読み方</TableCell>
                      <TableCell align="right" sx={{ fontWeight: 600, color: "text.secondary", fontSize: "0.875rem" }}>操作</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {guildDictionary.map((entry) => (
                      <TableRow key={entry.key} hover>
                        <TableCell sx={{ fontWeight: 500 }}>{entry.key}</TableCell>
                        <TableCell>
                          {guildDictEditKey === entry.key ? (
                            <TextField
                              size="small"
                              value={guildDictEditValue}
                              onChange={e => setGuildDictEditValue(e.target.value)}
                              disabled={guildDictLoading}
                              fullWidth
                            />
                          ) : (
                            entry.value
                          )}
                        </TableCell>
                        <TableCell align="right">
                          {guildDictEditKey === entry.key ? (
                            <Box sx={{ display: "flex", gap: 1, justifyContent: "flex-end" }}>
                              <Button
                                size="small"
                                onClick={handleEditGuildSave}
                                disabled={guildDictLoading}
                                sx={{ textTransform: "none" }}
                              >
                                保存
                              </Button>
                              <Button
                                size="small"
                                onClick={() => setGuildDictEditKey(null)}
                                disabled={guildDictLoading}
                                sx={{ textTransform: "none" }}
                              >
                                キャンセル
                              </Button>
                            </Box>
                          ) : (
                            <Box sx={{ display: "flex", gap: 1, justifyContent: "flex-end" }}>
                              <Button
                                size="small"
                                onClick={() => handleEditGuildStart(entry.key, entry.value)}
                                disabled={guildDictLoading}
                                sx={{ textTransform: "none" }}
                              >
                                編集
                              </Button>
                              <Button
                                size="small"
                                color="error"
                                onClick={() => handleDeleteGuildDictionary(entry.key)}
                                disabled={guildDictLoading}
                                sx={{ textTransform: "none" }}
                              >
                                削除
                              </Button>
                            </Box>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            )}
          </CardContent>
        </Card>

        {/* ユーザー辞書管理カード */}
        <Card elevation={0} sx={{ border: 1, borderColor: "divider" }}>
          <CardContent sx={{ p: 3 }}>
            <Typography variant="h6" sx={{ fontWeight: 500, mb: 0.5 }}>
              ユーザー辞書
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
              ユーザー辞書とは、すべてのサーバーで共通して使用される辞書です。
              ユーザー単位に登録されるため、参加しているすべてのサーバーで同じ辞書が利用されます。
            </Typography>

            {dictError && (
              <Paper elevation={0} sx={{ p: 2, mb: 2, bgcolor: "#fdecea", border: 1, borderColor: "#f5c6cb" }}>
                <Typography variant="body2" color="error">{dictError}</Typography>
              </Paper>
            )}

            {/* 追加フォーム */}
            <Paper elevation={0} sx={{ p: 2, mb: 3, bgcolor: "#f5f5f5" }}>
              <form onSubmit={handleAddDictionary}>
                <Box sx={{ display: "flex", gap: 2, alignItems: "flex-start" }}>
                  <TextField
                    size="small"
                    label="キー"
                    value={dictKey}
                    onChange={e => setDictKey(e.target.value)}
                    disabled={dictLoading}
                    sx={{ width: 200, bgcolor: "white" }}
                  />
                  <TextField
                    size="small"
                    label="値（読み方）"
                    value={dictValue}
                    onChange={e => setDictValue(e.target.value)}
                    disabled={dictLoading}
                    sx={{ width: 280, bgcolor: "white" }}
                  />
                  <Button
                    type="submit"
                    variant="contained"
                    disabled={dictLoading || !dictKey || !dictValue}
                    sx={{
                      bgcolor: "#1976d2",
                      textTransform: "none",
                      boxShadow: "none",
                      "&:hover": { boxShadow: 1 }
                    }}
                  >
                    追加
                  </Button>
                </Box>
              </form>
            </Paper>

            {/* 辞書テーブル */}
            {dictLoading ? (
              <Typography>読み込み中…</Typography>
            ) : userDictionary.length === 0 ? (
              <Box sx={{ textAlign: "center", py: 4 }}>
                <Typography variant="body2" color="text.secondary">
                  辞書エントリがありません。上のフォームから追加してください。
                </Typography>
              </Box>
            ) : (
              <TableContainer>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell sx={{ fontWeight: 600, color: "text.secondary", fontSize: "0.875rem" }}>キー</TableCell>
                      <TableCell sx={{ fontWeight: 600, color: "text.secondary", fontSize: "0.875rem" }}>読み方</TableCell>
                      <TableCell align="right" sx={{ fontWeight: 600, color: "text.secondary", fontSize: "0.875rem" }}>操作</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {userDictionary.map((entry) => (
                      <TableRow key={entry.key} hover>
                        <TableCell sx={{ fontWeight: 500 }}>{entry.key}</TableCell>
                        <TableCell>
                          {dictEditKey === entry.key ? (
                            <TextField
                              size="small"
                              value={dictEditValue}
                              onChange={e => setDictEditValue(e.target.value)}
                              disabled={dictLoading}
                              fullWidth
                            />
                          ) : (
                            entry.value
                          )}
                        </TableCell>
                        <TableCell align="right">
                          {dictEditKey === entry.key ? (
                            <Box sx={{ display: "flex", gap: 1, justifyContent: "flex-end" }}>
                              <Button
                                size="small"
                                onClick={handleEditSave}
                                disabled={dictLoading}
                                sx={{ textTransform: "none" }}
                              >
                                保存
                              </Button>
                              <Button
                                size="small"
                                onClick={() => setDictEditKey(null)}
                                disabled={dictLoading}
                                sx={{ textTransform: "none" }}
                              >
                                キャンセル
                              </Button>
                            </Box>
                          ) : (
                            <Box sx={{ display: "flex", gap: 1, justifyContent: "flex-end" }}>
                              <Button
                                size="small"
                                onClick={() => handleEditStart(entry.key, entry.value)}
                                disabled={dictLoading}
                                sx={{ textTransform: "none" }}
                              >
                                編集
                              </Button>
                              <Button
                                size="small"
                                color="error"
                                onClick={() => handleDeleteDictionary(entry.key)}
                                disabled={dictLoading}
                                sx={{ textTransform: "none" }}
                              >
                                削除
                              </Button>
                            </Box>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            )}
          </CardContent>
        </Card>
      </Container>
    </Box>
  );
}

