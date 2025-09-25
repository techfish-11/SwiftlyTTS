import React from 'react';
import { Box } from '@mui/material';
import CloudIcon from '@mui/icons-material/Cloud';

// 雲と箱が降りてくるアニメーション
const CloudDownloadAnimation: React.FC = () => (
  <Box
    sx={{
      width: 200,
      height: 180,
      position: 'relative',
      mb: 4,
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'flex-start',
    }}
  >
    {/* 雲（Material UIアイコン） */}
    <CloudIcon
      sx={{
        position: 'absolute',
        top: 0,
        left: 35,
        fontSize: 120,
        color: '#e0e7ef',
        zIndex: 2,
        filter: 'drop-shadow(0 2px 8px #b0b8c1)',
      }}
    />
    {/* 箱が降りてくるアニメーション */}
    {[0, 1, 2].map(i => (
      <svg
        key={i}
        width="40"
        height="40"
        style={{
          position: 'absolute',
          left: 80 + i * 20 - 20,
          top: 40,
          zIndex: 1,
          animation: `boxDrop 1.2s ${i * 0.3}s infinite cubic-bezier(.4,2,.6,1)`,
        }}
      >
        {/* 箱（ダンボール風） */}
        <rect x="8" y="8" width="24" height="24" rx="3" fill="#c8a96a" stroke="#a07d3b" strokeWidth="2" />
        <rect x="8" y="8" width="24" height="8" fill="#e2c48d" />
        <rect x="18" y="8" width="4" height="8" fill="#b89b5b" />
      </svg>
    ))}
    {/* アニメーションCSS */}
    <style>
      {`
        @keyframes boxDrop {
          0% {
            opacity: 0;
            transform: translateY(-10px) scale(0.7);
          }
          10% {
            opacity: 1;
            transform: translateY(0) scale(1);
          }
          80% {
            opacity: 1;
            transform: translateY(80px) scale(1);
          }
          100% {
            opacity: 0;
            transform: translateY(120px) scale(0.7);
          }
        }
      `}
    </style>
  </Box>
);

const Loading: React.FC = () => {
  return (
    <Box
      sx={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: '100vh',
        backgroundColor: 'background.default',
        flexDirection: 'column',
        gap: 4,
      }}
    >
      <CloudDownloadAnimation />
      <Box
        sx={{
          typography: 'h6',
          color: 'onSurface.main',
          textAlign: 'center',
        }}
      >
        データをダウンロードしています...
      </Box>
    </Box>
  );
};

export default Loading;