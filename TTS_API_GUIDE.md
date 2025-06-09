# Gemini TTS API ガイド

このガイドでは、Gemini TTS APIの音声オプションと使用方法について説明します。

## 利用可能な音声（全30種類）

### 女性音声（11種類）

| ID | 名前 | スタイル | 特徴 | 推奨用途 |
|---|---|---|---|---|
| kore | Kore | 会社的 | プロフェッショナルで標準的 | ビジネス会話、フォーマルな場面 |
| aoede | Aoede | 軽快 | 明るく軽やか | カジュアルな会話、友好的な雰囲気 |
| callirrhoe | Callirrhoe | おおらか | 寛容で穏やか | リラックスした会話、相談場面 |
| leda | Leda | 若々しい | 活発でエネルギッシュ | 若者向けコンテンツ、元気な雰囲気 |
| algieba | Algieba | スムーズ | 流暢で聞きやすい | ナレーション、説明 |
| autonoe | Autonoe | 明るい | 楽観的で前向き | 励まし、ポジティブなメッセージ |
| despina | Despina | スムーズ | 落ち着いて滑らか | 瞑想、リラクゼーション |
| erinome | Erinome | クリア | 明瞭で聞き取りやすい | アナウンス、重要な情報伝達 |
| laomedeia | Laomedeia | アップビート | 活気があり楽しい | イベント案内、エンターテイメント |
| pulcherrima | Pulcherrima | 前向き | 積極的で自信に満ちた | モチベーション、コーチング |
| vindemiatrix | Vindemiatrix | 優しい | 思いやりがあり温かい | 慰め、サポート、癒し |

### 男性音声（15種類）

| ID | 名前 | スタイル | 特徴 | 推奨用途 |
|---|---|---|---|---|
| enceladus | Enceladus | 息づかい | 自然で人間的 | 親密な会話、ささやき |
| charon | Charon | 情報提供的 | 知的で説得力がある | ニュース、解説、教育 |
| fenrir | Fenrir | 興奮しやすい | エネルギッシュで情熱的 | スポーツ実況、興奮場面 |
| orus | Orus | 会社的 | フォーマルでビジネスライク | 企業案内、公式発表 |
| iapetus | Iapetus | クリア | 明確で聞き取りやすい | 指示、ガイダンス |
| algenib | Algenib | 砂利声 | 重厚で威厳がある | 権威的な発言、強い主張 |
| rasalgethi | Rasalgethi | 情報豊富 | 知識豊かで信頼できる | 専門的な解説、講義 |
| achernar | Achernar | ソフト | 穏やかで優しい | 子供向け、リラックス |
| alnilam | Alnilam | 確実 | 自信に満ちて信頼できる | 重要な発表、決定事項 |
| gacrux | Gacrux | 成熟 | 落ち着いて大人びた | アドバイス、経験談 |
| achird | Achird | フレンドリー | 親しみやすく温かい | カスタマーサービス、案内 |
| zubenelgenubi | Zubenelgenubi | カジュアル | リラックスして気楽 | 日常会話、雑談 |
| sadachbia | Sadachbia | 活発 | 元気で生き生きとした | エンターテイメント、活動案内 |
| sadaltager | Sadaltager | 知識豊富 | 博識で教養がある | 教育コンテンツ、専門解説 |
| sulafat | Sulafat | 温かい | 心温まる優しさ | 励まし、感謝のメッセージ |

### 中性音声（4種類）

| ID | 名前 | スタイル | 特徴 | 推奨用途 |
|---|---|---|---|---|
| puck | Puck | アップビート | 陽気で楽しい | 子供向け、ゲーム、楽しい案内 |
| zephyr | Zephyr | 明るい | 軽快で前向き | 一般的な案内、明るい雰囲気 |
| umbriel | Umbriel | 気楽 | のんびりとリラックス | カジュアルな会話、休憩案内 |
| schedar | Schedar | 均等 | バランスが取れて中立的 | システム音声、中立的な案内 |

## 使用方法

### 基本的な使用

```javascript
// 特定の音声を指定
const response = await fetch('/api/tts', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
        text: "こんにちは",
        voice: "kore"  // 音声IDを指定
    })
});
```

### 感情による自動音声選択

```javascript
// 感情を指定すると最適な音声が自動選択される
const response = await fetch('/api/tts', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
        text: "やった！成功しました！",
        emotion: "excited"  // fenrir（興奮しやすい）が選択される
    })
});
```

### カスタムスタイルの適用

```javascript
// カスタムプロンプトで細かい制御
const response = await fetch('/api/tts', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
        text: "重要なお知らせがあります",
        voice: "alnilam",
        style: "with authority and clarity"
    })
});
```

## 感情と推奨音声のマッピング

| 感情 | 推奨音声 | 理由 |
|---|---|---|
| happy（楽しい） | autonoe | 明るい女性音声で幸せな感情を表現 |
| excited（興奮） | fenrir | 興奮しやすい男性音声でエネルギーを表現 |
| sad（悲しい） | vindemiatrix | 優しい女性音声で慰めの雰囲気 |
| tired（疲れ） | enceladus | 息づかいのある音声で疲労感を表現 |
| angry（怒り） | algenib | 砂利声で強い感情を表現 |
| worried（心配） | achernar | ソフトな男性音声で不安を和らげる |
| calm（落ち着き） | schedar | 均等な中性音声で平静さを表現 |
| confident（自信） | alnilam | 確実な男性音声で自信を表現 |
| professional（プロ） | orus | 会社的な男性音声でフォーマルさを表現 |
| friendly（親しみ） | achird | フレンドリーな男性音声で親近感 |

## ベストプラクティス

1. **シーンに応じた音声選択**
   - ビジネス場面: kore, orus
   - カジュアル会話: aoede, zubenelgenubi
   - 教育・説明: charon, rasalgethi
   - 感情表現: 各感情に対応した音声

2. **音声の一貫性**
   - 同じキャラクターには同じ音声を使用
   - シーンが変わっても基本的な音声は維持

3. **感情の自動検出を活用**
   - AIの応答に含まれる感情表現を自動検出
   - 適切な音声が自動選択される

4. **カスタムスタイルの活用**
   - 特定の雰囲気を出したい場合はstyleパラメータを使用
   - 英語のプロンプトが効果的（例: "in a mysterious way"）