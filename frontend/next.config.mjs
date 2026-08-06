/** @type {import('next').NextConfig} */
const nextConfig = {
  outputFileTracingRoot: process.cwd(),
  webpack(config) {
    config.resolve.alias = {
      ...config.resolve.alias,
      "@react-native-async-storage/async-storage": false,
      "pino-pretty": false,
    };
    return config;
  },
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "cdn.jsdelivr.net",
        port: "",
      },
      {
        protocol: "https",
        hostname: "gateway.pinata.cloud",
        pathname: "/ipfs/**",
      },
      {
        protocol: "https",
        hostname: "**.mypinata.cloud",
        pathname: "/ipfs/**",
      },
      {
        protocol: "https",
        hostname: "ipfs.io",
        pathname: "/ipfs/**",
      },
      {
        protocol: "https",
        hostname: "fanora-1251127085.cos.ap-guangzhou.myqcloud.com",
      },
      {
        protocol: "https",
        hostname: "**.imglnk.cn",
        pathname: "/v/**",
      },
      {
        protocol: "https",
        hostname: "s3.siliconflow.cn",
        pathname: "/temporary/outputs/**",
      },
    ],
  },
};

export default nextConfig;
