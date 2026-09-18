# Terraform / Infrastructure as Code

## Cel i zakres

Infrastruktura platformy DocMind jest zarządzana w modelu **Infrastructure as Code (IaC)** przy użyciu Terraform. Kod deklaratywnie opisuje zasoby Azure wymagane do działania platformy, ich konfigurację, zależności oraz przypisania uprawnień. Dzięki temu środowiska DEV, TEST i PROD są wdrażane w powtarzalny, kontrolowany i audytowalny sposób.

Zakres automatyzacji obejmuje w szczególności:

- sieć wirtualną, podsieci, Private Endpoints i integrację z prywatnymi strefami DNS;
- tożsamości zarządzane (User Assigned Managed Identities) wykorzystywane przez usługi oraz mechanizmy CMK;
- role Azure RBAC dla aplikacji, pipeline'ów i tożsamości zarządzanych;
- podstawowe usługi platformy: Azure Container Registry, Key Vault, Storage Account, PostgreSQL Flexible Server, Service Bus, Azure AI Services oraz środowisko Azure Container Apps;
- runtime aplikacji: Container Apps, komponenty Dapr, zadanie migracji bazy danych oraz konfigurację obrazów kontenerowych;
- stos Langfuse, wdrażany w niezależnych warstwach Core, Network i RBAC.

Terraform nie przechowuje wartości sekretów aplikacyjnych w plikach konfiguracyjnych. Sekrety są zarządzane w Azure Key Vault i przekazywane do usług za pomocą referencji Key Vault oraz tożsamości zarządzanych.

> **PLACEHOLDER – diagram architektury IaC:** tutaj należy wkleić diagram pokazujący GitHub Actions, self-hosted runner, Azure Blob Storage backend, Terraform oraz zasoby Azure zarządzane przez poszczególne moduły.

## Struktura rozwiązania

Kod Terraform jest podzielony na niezależne root modules oraz osobne pliki stanu. Podział ogranicza zakres uprawnień każdego pipeline'u i zmniejsza ryzyko niezamierzonych zmian w innych obszarach platformy.

| Obszar | Odpowiedzialność |
|---|---|
| `network` | Foundation sieci, Private DNS links oraz Private Endpoints zasobów platformy |
| `uami-cmk` | Tożsamości zarządzane używane do dostępu do kluczy CMK |
| `rbac-cmk` | Uprawnienia UAMI do kluczy Customer Managed Keys w Key Vault |
| `core` | Usługi platformowe i runtime aplikacji, wdrażane etapowo |
| `rbac` | Uprawnienia Azure RBAC dla workload identities i pipeline'ów GitHub Actions |
| `langfuse-network` | Private Endpoints zasobów Langfuse |
| `langfuse-rbac` | Dostęp UAMI Langfuse oraz LLMMagic do ACR i sekretów Key Vault |
| `langfuse-core` | Tożsamości, storage oraz runtime Langfuse |

Każdy root module posiada odrębny plik stanu przechowywany w prywatnym Azure Storage Account. Stan nie jest współdzielony pomiędzy środowiskami ani pomiędzy obszarami odpowiedzialności.

## Środowiska i parametryzacja

Konfiguracja jest parametryzowana per środowisko przez pliki `env/<environment>.tfvars`. Pliki zawierają wyłącznie wartości niebędące sekretami, m.in. nazwy zasobów, identyfikatory subskrypcji, CIDR-y, nazwy sieci, identyfikatory obrazów oraz referencje do wersjonowanych kluczy CMK.

Obsługiwane środowiska:

- `dev` – środowisko deweloperskie;
- `test` – środowisko testowe;
- `prod` – środowisko produkcyjne.

Zmiana konfiguracji środowiska jest realizowana przez pull request, przegląd kodu oraz kontrolowany workflow GitHub Actions. Terraform plan jest zawsze wykonywany przed apply i stanowi element akceptacji zmiany.

> **PLACEHOLDER – screen GitHub Environments:** tutaj należy wkleić screen środowisk `dev`, `test` i `prod` z widocznymi zasadami ochrony wdrożeń, bez ujawniania wartości sekretów.

## Proces wdrożenia

Wdrożenie nowego środowiska odbywa się sekwencyjnie. Kolejność eliminuje zależności cykliczne, w szczególności pomiędzy prywatną siecią, tożsamościami, rolami RBAC oraz usługami korzystającymi z Private Endpoints.

1. Network Foundation – utworzenie lub konfiguracja fundamentów sieci.
2. UAMI CMK Foundation – utworzenie tożsamości dla szyfrowania CMK.
3. RBAC CMK – nadanie UAMI dostępu do kluczy Key Vault.
4. Core Foundation – utworzenie usług bazowych platformy bez runtime aplikacji.
5. Network Completion – utworzenie wszystkich Private Endpoints i rekordów DNS.
6. RBAC – nadanie wymaganych uprawnień usługom i pipeline'om.
7. Application Build – budowa obrazów z kodu znajdującego się w repozytorium i publikacja do prywatnego ACR.
8. Core Runtime – utworzenie Container Apps, komponentów Dapr oraz zadania migracji bazy danych.
9. Application Deploy – migracja bazy danych i aktualizacja aplikacji obrazami wskazanymi przez pełny commit SHA.

Langfuse jest wdrażany jako niezależny stos: Langfuse Core Foundation, Langfuse Network, Langfuse RBAC, bootstrap sekretów, a następnie Langfuse Core Runtime. Dopiero po zakończeniu tego procesu aktywowana jest integracja tracingu Langfuse w runtime aplikacji.

> **PLACEHOLDER – screen przykładowego Terraform plan:** tutaj należy wkleić screen z GitHub Actions pokazujący plan Terraform dla PROD, z widocznym podsumowaniem `Plan: ... to add, ... to change, ... to destroy`. Screen nie może zawierać sekretów ani wrażliwych connection stringów.

## CI/CD i kontrola dostępu

Workflows GitHub Actions są uruchamiane na dedykowanych self-hosted runnerach przypisanych do środowiska. Runner jest wybierany dynamicznie na podstawie nazwy GitHub Environment: `dev`, `test` lub `prod`. Zapobiega to przypadkowemu uruchomieniu wdrożenia TEST albo PROD z sieci innego środowiska.

Pipeline'y uwierzytelniają się do Azure przez OpenID Connect (OIDC) i federowane Service Principals. Nie używają długoterminowych client secrets do logowania w Azure. Każdy SPN otrzymuje wyłącznie role konieczne do realizacji przypisanej odpowiedzialności, np. odczyt/push obrazów w ACR, wdrażanie Container Apps lub zarządzanie stanem Terraform.

Backend Terraform korzysta z uwierzytelniania Microsoft Entra ID (`use_azuread_auth=true`). Dostęp do backendu oraz zasobów prywatnych jest możliwy tylko z runnera mającego właściwą ścieżkę sieciową i rozwiązywanie prywatnego DNS.

> **PLACEHOLDER – screen workflow:** tutaj należy wkleić screen listy uruchomień GitHub Actions, na którym widoczne są nazwy workflow zawierające środowisko oraz tryb `plan` albo `plan + apply`.

## Zasady bezpieczeństwa i eksploatacji

- Wszystkie zmiany infrastrukturalne wymagają wcześniejszego Terraform plan oraz jego przeglądu.
- Apply jest dozwolone wyłącznie z chronionej gałęzi `main` i w kontekście odpowiedniego GitHub Environment.
- Zasoby korzystające z danych aplikacyjnych są dostępne prywatnie przez Private Endpoints; publiczny dostęp jest wyłączony tam, gdzie wymaga tego architektura.
- Dostęp do sekretów jest realizowany przez Azure Key Vault. Terraform przechowuje referencje do sekretów, nie ich wartości.
- Klucze CMK są identyfikowane przez wersjonowane URI. Zmiana klucza wymaga kontrolowanej zmiany konfiguracji i weryfikacji uprawnień UAMI do nowego klucza.
- Obrazy aplikacyjne są identyfikowane pełnym SHA commitu i digestem rejestru ACR, co zapewnia identyfikowalność wdrożonej wersji.
- Po każdym apply wykonywany jest ponowny plan. Oczekiwanym wynikiem dla niezmienionej konfiguracji jest `No changes`.

## Odpowiedzialności operacyjne

| Obszar | Odpowiedzialność operacyjna |
|---|---|
| Kod Terraform i workflow | Zespół wdrożeniowy / DevOps |
| Przegląd planów i akceptacja apply | Właściciel środowiska oraz osoby upoważnione w GitHub Environment |
| Zarządzanie sekretami | Właściciel Key Vault zgodnie z modelem RBAC |
| Sieć, Private DNS i Private Endpoints | Zespół Azure Network / platformowy |
| Monitoring wdrożeń i diagnostyka | Zespół aplikacyjny oraz DevOps |

> **PLACEHOLDER – screen Azure IAM / Key Vault:** tutaj należy wkleić screen pokazujący model RBAC dla Key Vault lub ACR, z zamazanymi identyfikatorami użytkowników oraz bez wartości sekretów.
