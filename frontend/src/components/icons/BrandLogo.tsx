import React from 'react';

interface BrandLogoProps {
  className?: string;
  size?: number;
}

export const BrandLogo: React.FC<BrandLogoProps> = ({ className = '', size = 32 }) => {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 64 64"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={`shrink-0 ${className}`}
    >
      {/* Outer Rounded Container */}
      <rect width="64" height="64" rx="16" fill="url(#iq_bg_grad)" />

      {/* Baseline */}
      <path d="M15 50H49" stroke="#A78BFA" strokeWidth="2.5" strokeLinecap="round" opacity="0.6" />

      {/* Bar Chart (3 Ascending Bars) */}
      <rect x="18" y="36" width="5" height="14" rx="2.5" fill="url(#bar_grad1)" />
      <rect x="25" y="30" width="5" height="20" rx="2.5" fill="url(#bar_grad2)" />
      <rect x="32" y="24" width="5" height="26" rx="2.5" fill="url(#bar_grad3)" />

      {/* Magnifying Glass Lens & Handle */}
      <circle cx="41" cy="27" r="10" stroke="white" strokeWidth="3.5" fill="none" />
      <path d="M48 34L55 41" stroke="white" strokeWidth="4" strokeLinecap="round" />

      {/* Center Spark Indicator */}
      <path
        d="M41 23C41 23 43 25.5 43 27C43 28.1 42.1 29 41 29C39.9 29 39 28.1 39 27C39 25.5 41 23 41 23Z"
        fill="#FBBF24"
      />

      <defs>
        <linearGradient id="iq_bg_grad" x1="0" y1="0" x2="64" y2="64" gradientUnits="userSpaceOnUse">
          <stop stopColor="#6366F1" />
          <stop offset="1" stopColor="#7C3AED" />
        </linearGradient>
        <linearGradient id="bar_grad1" x1="20.5" y1="36" x2="20.5" y2="50" gradientUnits="userSpaceOnUse">
          <stop stopColor="#FFFFFF" stopOpacity="0.9" />
          <stop offset="1" stopColor="#C4B5FD" stopOpacity="0.7" />
        </linearGradient>
        <linearGradient id="bar_grad2" x1="27.5" y1="30" x2="27.5" y2="50" gradientUnits="userSpaceOnUse">
          <stop stopColor="#FFFFFF" stopOpacity="0.95" />
          <stop offset="1" stopColor="#DDD6FE" stopOpacity="0.75" />
        </linearGradient>
        <linearGradient id="bar_grad3" x1="34.5" y1="24" x2="34.5" y2="50" gradientUnits="userSpaceOnUse">
          <stop stopColor="#FFFFFF" />
          <stop offset="1" stopColor="#EDE9FE" stopOpacity="0.8" />
        </linearGradient>
      </defs>
    </svg>
  );
};
