"use client";
import { useEffect } from "react";
import { signIn, useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import Box from "@mui/material/Box";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import Container from "@mui/material/Container";
import Divider from "@mui/material/Divider";
import { FaDiscord } from "react-icons/fa";

export default function SignInPage() {
  const { data: session, status } = useSession();
  const router = useRouter();

  useEffect(() => {
    if (status === "authenticated") {
      // Replace so user can't go back to signin with back button
      router.replace("/dashboard");
    }
  }, [status, router]);

  if (status === "authenticated") {
    return (
      <Box
        sx={{
          minHeight: "100vh",
          bgcolor: "#f8f9fa",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          py: 4,
        }}
      >
        <Typography variant="h6" color="text.secondary">
          リダイレクト中…
        </Typography>
      </Box>
    );
  }
  return (
    <Box
      sx={{
        minHeight: "100vh",
        bgcolor: "#f8f9fa",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        py: 4,
      }}
    >
      <Container maxWidth="sm">
        <Paper
          elevation={0}
          sx={{
            p: { xs: 4, sm: 6 },
            borderRadius: 3,
            border: "1px solid",
            borderColor: "divider",
            bgcolor: "#ffffff",
            maxWidth: 480,
            mx: "auto",
            transition: "box-shadow 0.3s ease-in-out",
            "&:hover": {
              boxShadow: "0 2px 12px rgba(0,0,0,0.08)",
            },
          }}
        >
          <Stack spacing={4} alignItems="center">
            {/* Logo Section */}
            <Box
              sx={{
                width: 80,
                height: 80,
                borderRadius: "20px",
                bgcolor: "#5865F2",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                boxShadow: "0 4px 16px rgba(88,101,242,0.24)",
              }}
            >
              <FaDiscord size={44} color="#fff" />
            </Box>

            {/* Title Section */}
            <Stack spacing={1} alignItems="center" width="100%">
              <Typography
                variant="h4"
                fontWeight={500}
                color="text.primary"
                sx={{
                  fontSize: { xs: "1.75rem", sm: "2rem" },
                  letterSpacing: "-0.5px",
                }}
              >
                Swiftly読み上げbot
              </Typography>
              <Typography
                variant="body1"
                color="text.secondary"
                align="center"
                sx={{
                  fontSize: "1rem",
                  lineHeight: 1.6,
                  maxWidth: 360,
                }}
              >
                ダッシュボードにアクセスするには、Discordアカウントでログインしてください
              </Typography>
            </Stack>

            <Divider sx={{ width: "100%", my: 2 }} />

            {/* Sign In Button */}
            <Button
              variant="outlined"
              size="large"
              fullWidth
              startIcon={<FaDiscord size={24} />}
              sx={{
                borderColor: "#dadce0",
                color: "#3c4043",
                fontWeight: 600,
                borderRadius: "8px",
                textTransform: "none",
                fontSize: "15px",
                px: 3,
                py: 1.75,
                border: "1.5px solid #dadce0",
                transition: "all 0.2s ease-in-out",
                "&:hover": {
                  bgcolor: "#f8f9fa",
                  borderColor: "#5865F2",
                  color: "#5865F2",
                  boxShadow: "0 1px 4px rgba(0,0,0,0.1)",
                },
                "&:active": {
                  bgcolor: "#e8eaed",
                },
                "& .MuiButton-startIcon": {
                  color: "#5865F2",
                },
              }}
              onClick={() =>
                signIn("discord", {
                  callbackUrl: `${window.location.origin}/dashboard`,
                })
              }
            >
              Discordでログイン
            </Button>

            {/* Footer Text */}
            <Typography
              variant="caption"
              color="text.secondary"
              align="center"
              sx={{
                fontSize: "0.75rem",
                lineHeight: 1.5,
                maxWidth: 340,
                pt: 2,
              }}
            >
              ログインすることで、SwiftlyTTSの
              <Box
                component="a"
                href="https://github.com/techfish-11/SwiftlyTTS/blob/main/terms-privacy/terms.md"
                target="_blank"
                rel="noopener noreferrer"
                sx={{ color: "#5865F2", fontWeight: 600, textDecoration: "underline", mx: 0.5 }}
              >
                利用規約
              </Box>
              と
              <Box
                component="a"
                href="https://github.com/techfish-11/SwiftlyTTS/blob/main/terms-privacy/privacy.md"
                target="_blank"
                rel="noopener noreferrer"
                sx={{ color: "#5865F2", fontWeight: 600, textDecoration: "underline", mx: 0.5 }}
              >
                プライバシーポリシー
              </Box>
              に同意したことになります
            </Typography>
          </Stack>
        </Paper>
      </Container>
    </Box>
  );
}
