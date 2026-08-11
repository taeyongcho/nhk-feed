# 안드로이드 네이티브 APK 빌드 워크플로 (템플릿)

GitHub Actions로 APK를 자동 빌드·서명·배포하기 위한 템플릿입니다.

> ⚠️ **이 폴더의 yml은 여기서 실행되지 않습니다.** `nhk-feed`에는 Gradle 프로젝트가 없기 때문에
> 일부러 `.github/workflows/`가 아닌 `docs/` 아래에 두었습니다.
> **안드로이드 앱 repo로 복사해서 사용하세요.**

| 파일 | 언제 도는가 | 무엇을 하는가 |
|---|---|---|
| `android-ci.yml` | main 푸시 / PR | 유닛테스트 + 린트 + **디버그 APK** |
| `android-release.yml` | `v*` 태그 푸시 / 수동 | **서명된 릴리스 APK**(+AAB) → GitHub Release |

---

## 1. 워크플로 파일 복사

안드로이드 repo에서:

```bash
mkdir -p .github/workflows
# 이 폴더의 두 yml을 그대로 복사
cp android-ci.yml android-release.yml .github/workflows/
```

**모듈 이름이 `app`이 아니라면** yml 안의 `app/build/outputs/...` 경로를 실제 모듈명으로 바꾸세요.

## 2. 서명 키스토어 만들기 (최초 1회, 내 PC에서)

```bash
keytool -genkeypair -v \
  -keystore release.jks \
  -alias upload \
  -keyalg RSA -keysize 2048 -validity 10000
```

> 🔴 **이 `release.jks` 파일과 비밀번호는 절대 잃어버리면 안 됩니다.**
> 분실하면 같은 앱으로 업데이트를 낼 수 없습니다(패키지명이 같아도 서명이 다르면 설치 거부).
> PC 외 안전한 곳에 별도 백업해 두세요.
>
> 🔴 **키스토어를 git에 커밋하지 마세요.** `.gitignore`에 아래를 추가하세요:
> ```gitignore
> *.jks
> *.keystore
> keystore.properties
> local.properties
> ```

## 3. 키스토어를 base64로 인코딩

시크릿에는 파일을 못 넣으므로 텍스트로 변환합니다.

```bash
# macOS / Linux
base64 -i release.jks | tr -d '\n' | pbcopy      # macOS (클립보드로 복사)
base64 -w0 release.jks > release.jks.base64      # Linux (파일로 저장)

# Windows PowerShell
[Convert]::ToBase64String([IO.File]::ReadAllBytes("release.jks")) | Set-Clipboard
```

## 4. Secrets 4개 등록

**안드로이드 repo** → Settings → Secrets and variables → **Actions** → New repository secret

| 이름 | 값 |
|---|---|
| `ANDROID_KEYSTORE_BASE64` | 3번에서 만든 base64 문자열 전체 |
| `ANDROID_KEYSTORE_PASSWORD` | 키스토어 비밀번호 |
| `ANDROID_KEY_ALIAS` | 키 별칭 (위 예시에서는 `upload`) |
| `ANDROID_KEY_PASSWORD` | 키 비밀번호 (보통 키스토어 비밀번호와 동일) |

> 시크릿은 **repo마다 따로** 등록해야 합니다. 다른 repo에 등록한 값은 보이지 않습니다.
> (Organization 계정이면 org 레벨 시크릿으로 여러 repo에 공유 가능)

## 5. 실행

```bash
# 릴리스 APK 만들기
git tag v1.0.0
git push origin v1.0.0
```

- 진행 상황: **Actions 탭**
- 결과물: 해당 실행의 **Artifacts** + repo **Releases** 페이지에 APK 첨부

수동 실행은 Actions → *Android Release* → **Run workflow** (AAB 동시 빌드 옵션 있음).

---

## 설계 메모

**서명 방식.** `build.gradle`을 건드리지 않아도 되도록 AGP의 주입 프로퍼티
(`-Pandroid.injected.signing.*`)를 사용합니다. 이미 `signingConfigs`를 환경변수로 읽도록
설정해 두셨다면 그 방식을 쓰고 이 `-P` 플래그들은 지우세요. 둘 다 쓰면 충돌합니다.

**키스토어 처리.** 작업 디렉터리가 아니라 `$RUNNER_TEMP`에 풀고, 성공·실패 관계없이
(`if: always()`) 삭제합니다. 실행기는 어차피 일회용이지만 아티팩트에 딸려 올라가는 사고를 막습니다.

**서명 검증.** `apksigner verify`로 서명이 실제로 붙었는지 확인한 뒤에만 업로드합니다.
서명 없는 APK가 Release에 올라가면 설치가 안 되므로 미리 걸러냅니다.

**JDK 버전.** AGP 8.x 이상 기준으로 21을 씁니다. 빌드가 JDK 버전 문제로 실패하면
`java-version`을 `17`로 낮춰보세요.

**캐시.** `gradle/actions/setup-gradle@v4`가 Gradle 배포판과 의존성을 자동 캐싱합니다.
별도 `actions/cache` 설정은 필요 없습니다.

**액션 버전.** 작성 시점 기준입니다. 나중에 `upload-artifact` 등에서 deprecation 경고가
뜨면 메이저 버전만 올리면 됩니다.
