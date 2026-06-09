import type { LucideIcon } from "lucide-react";

import { Card, CardDescription, CardTitle } from "@/components/ui/card";

type FeatureCardProps = {
  icon: LucideIcon;
  title: string;
  description: string;
};

export function FeatureCard({
  icon: Icon,
  title,
  description
}: FeatureCardProps) {
  return (
    <Card className="h-full border-white/8 bg-white/[0.03]">
      <div className="mb-5 flex h-12 w-12 items-center justify-center rounded-2xl border border-accent/20 bg-accent/10 text-accent">
        <Icon className="h-5 w-5" />
      </div>
      <CardTitle className="mb-3 text-lg">{title}</CardTitle>
      <CardDescription>{description}</CardDescription>
    </Card>
  );
}
