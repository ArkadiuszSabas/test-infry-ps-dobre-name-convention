"use client";

import { Building2Icon, LogInIcon } from "lucide-react";
import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { useReducer, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { BrandMark } from "@/components/ui/brand-mark";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Field,
  FieldError,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Notice } from "@/components/ui/notice";
import { PasswordInput } from "@/components/ui/password-input";
import { Spinner } from "@/components/ui/spinner";
import { useAuthActions } from "@/hooks/auth/auth-actions-context";
import { getLoginFormError } from "@/lib/auth/errors";
import type { Locale } from "@/i18n/routing";

interface LoginPageProps {
  isEntraLoginEnabled: boolean;
  locale: Locale;
  redirectTo: string | null;
}

interface LoginFormState {
  login: string;
  password: string;
  fieldErrors: {
    login?: string;
    password?: string;
  };
  formError: string | null;
  isSubmitting: boolean;
}

type LoginFormAction =
  | { type: "fieldChanged"; field: "login" | "password"; value: string }
  | {
      type: "validationFailed";
      fieldErrors: LoginFormState["fieldErrors"];
    }
  | { type: "submitStarted" }
  | { type: "submitFailed"; formError: string }
  | { type: "submitFinished" };

const initialState: LoginFormState = {
  fieldErrors: {},
  formError: null,
  isSubmitting: false,
  login: "",
  password: "",
};

export function LoginPage({
  isEntraLoginEnabled,
  locale,
  redirectTo,
}: LoginPageProps) {
  const t = useTranslations("Login");
  const passwordVisibility = useTranslations("PasswordVisibility");
  const router = useRouter();
  const { loginLocal, startEntraLogin } = useAuthActions();
  const [state, dispatch] = useReducer(loginFormReducer, initialState);
  const dashboardPath = `/${locale}`;
  const postLoginTarget = safeRedirectTo(redirectTo, locale) ?? dashboardPath;

  async function submitLocalLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const fieldErrors = validateFields(state, {
      loginRequired: t("fields.login.required"),
      passwordRequired: t("fields.password.required"),
    });

    if (Object.keys(fieldErrors).length > 0) {
      dispatch({ type: "validationFailed", fieldErrors });
      return;
    }

    dispatch({ type: "submitStarted" });

    try {
      await loginLocal({
        login: state.login,
        password: state.password,
      });
      router.replace(postLoginTarget);
    } catch (error) {
      const formError = getLoginFormError(error);
      dispatch({
        type: "submitFailed",
        formError: formError.values
          ? t(`errors.${formError.key}`, formError.values)
          : t(`errors.${formError.key}`),
      });
    } finally {
      dispatch({ type: "submitFinished" });
    }
  }

  function startEntra() {
    // The API exact-matches this URL against its Entra post-login allowlist.
    const redirectTarget = new URL(dashboardPath, window.location.origin);
    startEntraLogin(redirectTarget.toString());
  }

  return (
    <main className="flex h-dvh items-center justify-center overflow-y-auto bg-background px-6 py-10">
      <Card className="w-full max-w-[420px]">
        <CardHeader>
          <div className="mb-2 flex items-center gap-3">
            <BrandMark />
            <span className="text-lg font-semibold">DocMind.Ai</span>
          </div>
          <CardTitle aria-level={1} role="heading">
            {t("title")}
          </CardTitle>
          <CardDescription>{t("description")}</CardDescription>
        </CardHeader>
        <CardContent>
          <form
            aria-describedby={state.formError ? "login-form-error" : undefined}
            className="flex flex-col gap-4"
            onSubmit={submitLocalLogin}
          >
            <FieldGroup className="gap-4">
              <Field data-invalid={Boolean(state.fieldErrors.login)}>
                <FieldLabel htmlFor="login">
                  {t("fields.login.label")}
                </FieldLabel>
                <Input
                  id="login"
                  autoComplete="username"
                  aria-describedby={
                    state.fieldErrors.login ? "login-error" : undefined
                  }
                  aria-invalid={Boolean(state.fieldErrors.login)}
                  disabled={state.isSubmitting}
                  value={state.login}
                  onChange={(event) =>
                    dispatch({
                      type: "fieldChanged",
                      field: "login",
                      value: event.target.value,
                    })
                  }
                />
                {state.fieldErrors.login ? (
                  <FieldError id="login-error">
                    {state.fieldErrors.login}
                  </FieldError>
                ) : null}
              </Field>
              <Field data-invalid={Boolean(state.fieldErrors.password)}>
                <FieldLabel htmlFor="password">
                  {t("fields.password.label")}
                </FieldLabel>
                <PasswordInput
                  id="password"
                  autoComplete="current-password"
                  aria-describedby={
                    state.fieldErrors.password ? "password-error" : undefined
                  }
                  aria-invalid={Boolean(state.fieldErrors.password)}
                  disabled={state.isSubmitting}
                  hideLabel={passwordVisibility("hide")}
                  showLabel={passwordVisibility("show")}
                  value={state.password}
                  onChange={(event) =>
                    dispatch({
                      type: "fieldChanged",
                      field: "password",
                      value: event.target.value,
                    })
                  }
                />
                {state.fieldErrors.password ? (
                  <FieldError id="password-error">
                    {state.fieldErrors.password}
                  </FieldError>
                ) : null}
              </Field>
              {state.formError ? (
                <Notice
                  id="login-form-error"
                  title={state.formError}
                  tone="danger"
                />
              ) : null}
              <Button className="mt-1 h-10" disabled={state.isSubmitting}>
                {state.isSubmitting ? (
                  <Spinner data-icon="inline-start" />
                ) : (
                  <LogInIcon data-icon="inline-start" />
                )}
                {state.isSubmitting
                  ? t("actions.signingIn")
                  : t("actions.signIn")}
              </Button>
              {isEntraLoginEnabled ? (
                <Button
                  className="h-10"
                  disabled={state.isSubmitting}
                  onClick={startEntra}
                  type="button"
                  variant="outline"
                >
                  <Building2Icon data-icon="inline-start" />
                  {t("actions.entra")}
                </Button>
              ) : null}
            </FieldGroup>
          </form>
        </CardContent>
      </Card>
    </main>
  );
}

function loginFormReducer(
  state: LoginFormState,
  action: LoginFormAction,
): LoginFormState {
  switch (action.type) {
    case "fieldChanged":
      return {
        ...state,
        fieldErrors: {
          ...state.fieldErrors,
          [action.field]: undefined,
        },
        formError: null,
        [action.field]: action.value,
      };
    case "validationFailed":
      return {
        ...state,
        fieldErrors: action.fieldErrors,
        formError: null,
      };
    case "submitStarted":
      return {
        ...state,
        formError: null,
        isSubmitting: true,
      };
    case "submitFailed":
      return {
        ...state,
        formError: action.formError,
      };
    case "submitFinished":
      return {
        ...state,
        isSubmitting: false,
      };
  }
}

function validateFields(
  state: LoginFormState,
  messages: { loginRequired: string; passwordRequired: string },
): LoginFormState["fieldErrors"] {
  const fieldErrors: LoginFormState["fieldErrors"] = {};

  if (!state.login.trim()) {
    fieldErrors.login = messages.loginRequired;
  }

  if (!state.password) {
    fieldErrors.password = messages.passwordRequired;
  }

  return fieldErrors;
}

function safeRedirectTo(
  redirectTo: string | null,
  locale: Locale,
): string | null {
  if (!redirectTo || redirectTo.startsWith("//")) {
    return null;
  }

  if (redirectTo === `/${locale}` || redirectTo.startsWith(`/${locale}/`)) {
    return redirectTo;
  }

  if (
    redirectTo.startsWith(`/${locale}?`) ||
    redirectTo.startsWith(`/${locale}#`)
  ) {
    return redirectTo;
  }

  return null;
}
