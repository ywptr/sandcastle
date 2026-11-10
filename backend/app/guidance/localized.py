"""Conservative localized scaffolds; no translation of stored narrative or Canon."""
SCAFFOLDS = {
    "id": (["Langkah kecil", "Amati kembali", "Ungkapkan perasaan", "Pertimbangkan pilihan", "Tinjau tujuan"],
           "Gunakan kata sederhana dan nada lembut. Hormati fakta cerita dan tujuan yang sudah ada.", "Arahkan nada dan tempo dengan genre"),
    "ja": (["小さな一歩", "見直す", "気持ちを伝える", "選択を考える", "目標を振り返る"],
           "優しい言葉と穏やかな調子で、既存の事実と目標を守ってください。", "ジャンルを語調とテンポの参考にしてください"),
    "ko": (["작은 한 걸음", "다시 살펴보기", "감정 나누기", "선택 살펴보기", "목표 돌아보기"],
           "쉬운 말과 부드러운 어조로 기존 사실과 목표를 존중하세요.", "장르를 어조와 속도의 참고로 사용하세요"),
    "zh-CN": (["迈出小步", "重新观察", "表达感受", "考虑选择", "回顾目标"],
           "使用简单温和的语言，尊重已有事实和目标。", "用类型引导语气和节奏"),
    "fr": (["Un petit pas", "Observer à nouveau", "Exprimer un sentiment", "Examiner un choix", "Revoir le but"],
           "Utilisez des mots simples et un ton doux. Respectez les faits et le but établis.", "Guidez le ton et le rythme avec les genres"),
    "de": (["Ein kleiner Schritt", "Erneut betrachten", "Gefühle teilen", "Eine Wahl bedenken", "Das Ziel prüfen"],
           "Verwende einfache Worte und einen sanften Ton. Bewahre bestehende Fakten und Ziele.", "Nutze Genres für Ton und Tempo"),
    "es": (["Un paso pequeño", "Observar de nuevo", "Expresar un sentimiento", "Considerar una elección", "Revisar la meta"],
           "Usa palabras sencillas y un tono suave. Respeta los hechos y la meta establecidos.", "Orienta el tono y el ritmo con los géneros"),
}


def localized_choices(context):
    titles, instruction, genre_instruction = SCAFFOLDS[context.language]
    genres = [context.primary_genre] if context.primary_genre else []
    genres += context.secondary_genres
    # Taxonomy codes remain stable identifiers, never fabricated Story facts.
    suffix = f" {genre_instruction}: {', '.join(genres)}." if genres else ""
    return [(title, f"{title}. {instruction}{suffix}") for title in titles]
