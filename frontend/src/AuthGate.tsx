import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import {
  clearCredential,
  readCredential,
  saveCredential,
} from "./authSession";

export type AuthenticatedUser = {
  uid: string;
  email: string;
  email_verified: true;
  name: string;
  picture_url: string | null;
  provider: "google";
};

type GoogleAuthConfiguration = {
  enabled: boolean;
  client_id: string | null;
};

type GoogleLoginResponse = {
  created: boolean;
  user: AuthenticatedUser;
};

type GoogleCredentialResponse = {
  credential?: string;
};

type GoogleIdentityServices = {
  accounts: {
    id: {
      initialize(options: {
        client_id: string;
        callback(response: GoogleCredentialResponse): void;
        auto_select?: boolean;
        cancel_on_tap_outside?: boolean;
      }): void;
      renderButton(
        parent: HTMLElement,
        options: {
          theme: string;
          size: string;
          shape: string;
          text: string;
          width: number;
        },
      ): void;
      disableAutoSelect(): void;
    };
  };
};

declare global {
  interface Window {
    google?: GoogleIdentityServices;
  }
}

type AuthContextValue = {
  user: AuthenticatedUser;
  signOut(): void;
};

const AuthContext = createContext<AuthContextValue | null>(null);
const googleScriptUrl = "https://accounts.google.com/gsi/client";
let googleScriptPromise: Promise<void> | null = null;

function loadGoogleIdentityServices(): Promise<void> {
  if (window.google) {
    return Promise.resolve();
  }

  if (googleScriptPromise) {
    return googleScriptPromise;
  }

  googleScriptPromise = new Promise<void>((resolve, reject) => {
    const existing = document.querySelector<HTMLScriptElement>(
      `script[src="${googleScriptUrl}"]`,
    );

    const loaded = () => {
      if (window.google) {
        resolve();
      } else {
        reject(new Error("Google Identity Services did not initialize."));
      }
    };

    const failed = () => {
      googleScriptPromise = null;
      reject(new Error("Google Identity Services could not be loaded."));
    };

    if (existing) {
      existing.addEventListener("load", loaded, { once: true });
      existing.addEventListener("error", failed, { once: true });
      return;
    }

    const script = document.createElement("script");
    script.src = googleScriptUrl;
    script.async = true;
    script.defer = true;
    script.addEventListener("load", loaded, { once: true });
    script.addEventListener("error", failed, { once: true });
    document.head.append(script);
  });

  return googleScriptPromise;
}

async function responseDetail(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: unknown };
    if (typeof payload.detail === "string") {
      return payload.detail;
    }
  } catch {
    // The status code remains the authoritative fallback.
  }

  return `Authentication failed (HTTP ${response.status}).`;
}

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);
  if (!value) {
    throw new Error("Authentication context is unavailable.");
  }
  return value;
}

export default function AuthGate({ children }: { children: ReactNode }) {
  const buttonHost = useRef<HTMLDivElement>(null);
  const [configuration, setConfiguration] =
    useState<GoogleAuthConfiguration | null>(null);
  const [user, setUser] = useState<AuthenticatedUser | null>(null);
  const [booting, setBooting] = useState(true);
  const [signingIn, setSigningIn] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    async function bootstrap() {
      try {
        const configurationResponse = await window.fetch(
          "/v1/auth/config",
          {
            signal: controller.signal,
            headers: { Accept: "application/json" },
          },
        );

        if (!configurationResponse.ok) {
          throw new Error(
            `Authentication configuration is unavailable (HTTP ${configurationResponse.status}).`,
          );
        }

        const nextConfiguration =
          (await configurationResponse.json()) as GoogleAuthConfiguration;

        if (
          typeof nextConfiguration.enabled !== "boolean" ||
          (
            nextConfiguration.enabled &&
            !nextConfiguration.client_id
          )
        ) {
          throw new Error("Authentication configuration is invalid.");
        }

        if (!controller.signal.aborted) {
          setConfiguration(nextConfiguration);
        }

        const credential = readCredential();
        if (!credential) {
          return;
        }

        const profileResponse = await window.fetch("/v1/auth/me", {
          signal: controller.signal,
          headers: {
            Accept: "application/json",
            Authorization: `Bearer ${credential}`,
          },
        });

        if (!profileResponse.ok) {
          clearCredential();
          return;
        }

        const profile =
          (await profileResponse.json()) as AuthenticatedUser;

        if (!controller.signal.aborted) {
          setUser(profile);
        }
      } catch (caught: unknown) {
        if (
          !controller.signal.aborted &&
          !(caught instanceof DOMException && caught.name === "AbortError")
        ) {
          setError(
            caught instanceof Error
              ? caught.message
              : "Authentication initialization failed.",
          );
        }
      } finally {
        if (!controller.signal.aborted) {
          setBooting(false);
        }
      }
    }

    void bootstrap();
    return () => controller.abort();
  }, []);

  const completeGoogleLogin = useCallback(
    async (response: GoogleCredentialResponse) => {
      const credential = response.credential?.trim();
      if (!credential) {
        setError("Google did not return an identity credential.");
        return;
      }

      setSigningIn(true);
      setError(null);

      try {
        const loginResponse = await window.fetch("/v1/auth/google", {
          method: "POST",
          headers: {
            Accept: "application/json",
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ credential }),
        });

        if (!loginResponse.ok) {
          throw new Error(await responseDetail(loginResponse));
        }

        const payload =
          (await loginResponse.json()) as GoogleLoginResponse;

        saveCredential(credential);
        setUser(payload.user);
      } catch (caught: unknown) {
        clearCredential();
        setError(
          caught instanceof Error
            ? caught.message
            : "Google sign-in failed.",
        );
      } finally {
        setSigningIn(false);
      }
    },
    [],
  );

  useEffect(() => {
    if (
      booting ||
      user ||
      !configuration?.enabled ||
      !configuration.client_id
    ) {
      return;
    }

    let active = true;

    loadGoogleIdentityServices()
      .then(() => {
        if (!active || !buttonHost.current || !window.google) {
          return;
        }

        buttonHost.current.replaceChildren();
        window.google.accounts.id.initialize({
          client_id: configuration.client_id!,
          callback: completeGoogleLogin,
          auto_select: false,
          cancel_on_tap_outside: true,
        });
        window.google.accounts.id.renderButton(
          buttonHost.current,
          {
            theme: "filled_black",
            size: "large",
            shape: "pill",
            text: "continue_with",
            width: 280,
          },
        );
      })
      .catch((caught: unknown) => {
        if (active) {
          setError(
            caught instanceof Error
              ? caught.message
              : "Google sign-in could not be loaded.",
          );
        }
      });

    return () => {
      active = false;
    };
  }, [
    booting,
    completeGoogleLogin,
    configuration,
    user,
  ]);

  useEffect(() => {
    const unauthorized = () => {
      clearCredential();
      setUser(null);
      setError("Your session expired. Sign in again to continue.");
    };

    window.addEventListener(
      "scenefoundry:unauthorized",
      unauthorized,
    );
    return () => {
      window.removeEventListener(
        "scenefoundry:unauthorized",
        unauthorized,
      );
    };
  }, []);

  const signOut = useCallback(() => {
    clearCredential();
    window.google?.accounts.id.disableAutoSelect();
    setError(null);
    setUser(null);
  }, []);

  const context = useMemo<AuthContextValue | null>(
    () => user ? { user, signOut } : null,
    [signOut, user],
  );

  if (booting) {
    return (
      <div className="auth-shell">
        <div className="auth-loading" role="status">
          <span className="auth-orbit" aria-hidden="true" />
          <strong>Opening SceneFoundry</strong>
          <span>Verifying the production workspace?</span>
        </div>
      </div>
    );
  }

  if (!user || !context) {
    const configured = Boolean(
      configuration?.enabled && configuration.client_id,
    );

    return (
      <main className="auth-shell">
        <section className="auth-story">
          <div className="auth-brand">
            <span className="auth-brand-mark" aria-hidden="true">
              <span />
              <span />
              <span />
            </span>
            <span>
              <strong>SceneFoundry</strong>
              <small>AI CINEMA STUDIO</small>
            </span>
          </div>

          <div className="auth-copy">
            <p className="eyebrow">PRODUCTION INTELLIGENCE</p>
            <h1>From written idea to directed scene.</h1>
            <p>
              Develop scripts, ground production decisions, direct
              immutable scene revisions, and generate cinematic output
              from one accountable workspace.
            </p>
          </div>

          <div className="auth-pipeline" aria-label="SceneFoundry workflow">
            <span>Develop</span>
            <i aria-hidden="true" />
            <span>Direct</span>
            <i aria-hidden="true" />
            <span>Produce</span>
          </div>
        </section>

        <section className="auth-card" aria-labelledby="sign-in-title">
          <div>
            <p className="eyebrow">TRUSTED WORKSPACE</p>
            <h2 id="sign-in-title">Enter the studio</h2>
            <p>
              Sign in with a verified Google account to continue.
              Your production history stays tied to your identity.
            </p>
          </div>

          {configured ? (
            <div className="google-signin">
              <div ref={buttonHost} aria-label="Sign in with Google" />
              {signingIn && (
                <p role="status">Verifying your Google identity?</p>
              )}
            </div>
          ) : (
            <p className="auth-message" role="status">
              Google sign-in is not configured for this runtime.
            </p>
          )}

          {error && (
            <p className="auth-message error" role="alert">
              {error}
            </p>
          )}

          <div className="auth-assurance">
            <span>Server-verified identity</span>
            <span>Private media</span>
            <span>Immutable lineage</span>
          </div>
        </section>
      </main>
    );
  }

  return (
    <AuthContext.Provider value={context}>
      {children}
    </AuthContext.Provider>
  );
}
