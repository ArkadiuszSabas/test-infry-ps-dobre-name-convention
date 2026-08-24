export type GreetingPeriod = "morning" | "afternoon" | "evening";

export function getGreetingPeriod(hour: number): GreetingPeriod {
  if (hour >= 5 && hour < 12) {
    return "morning";
  }
  if (hour >= 12 && hour < 18) {
    return "afternoon";
  }
  return "evening";
}

export function getGreetingName(email: string | null): string | null {
  if (!email) {
    return null;
  }
  const localPart = email.split("@", 1)[0] ?? "";
  const firstSegment = localPart.split(/[._-]/, 1)[0] ?? "";
  const letters = /^\p{L}+/u.exec(firstSegment)?.[0] ?? "";
  if (letters.length === 0) {
    return null;
  }
  return (
    letters.charAt(0).toLocaleUpperCase() + letters.slice(1).toLocaleLowerCase()
  );
}
