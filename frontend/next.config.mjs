/** @type {import('next').NextConfig} */
const nextConfig = {
    output: process.env.NEXT_OUTPUT === "export" ? "export" : undefined,
};

export default nextConfig;
