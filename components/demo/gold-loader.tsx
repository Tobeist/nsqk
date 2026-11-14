"use client";
import dynamic from "next/dynamic";
const Gold = dynamic(() => import("./gold"), { ssr: false });
export default Gold;
