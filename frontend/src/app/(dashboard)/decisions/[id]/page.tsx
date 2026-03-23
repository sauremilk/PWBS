"use client";

import { useParams } from "next/navigation";
import { DecisionDetail } from "@/components/decisions/decision-detail";

export default function DecisionDetailPage() {
  const params = useParams<{ id: string }>();
  return <DecisionDetail id={params.id} />;
}
