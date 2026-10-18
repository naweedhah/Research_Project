import { redirect } from "next/navigation";

export default async function ChildTrajectoryRedirect({
  params,
}: {
  params: Promise<{ childId: string }> | { childId: string };
}) {
  const { childId } = await params;
  redirect(`/children/${childId}`);
}
