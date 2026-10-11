"""Shared, gold-free task instructions for annotation and evaluation."""
PROTOCOL_VERSION = "prefreeze-1"


def task_description(dataset, language):
    if "intent" in dataset:
        return ("Her kaydın ifade ettiği sesli asistan isteğini sınıflandır. Etiketler MASSIVE niyet kimlikleridir; alt çizgiler sözcükleri ayırır."
                if language == "tr" else
                "Classify the voice-assistant request expressed by each record. Labels are MASSIVE intent identifiers; underscores separate words.")
    if dataset == "interpress_tr":
        return ("Her haberin ana konusunu sınıflandır. ASCII etiketlerin anlamları: saglik=sağlık, gida=gıda, yasam=yaşam, egitim=eğitim, iletisim=iletişim, bilisim=bilişim, aktuel=aktüel, kultursanat=kültür ve sanat. Kaynak gazete bölümleri bazen örtüşür.")
    if dataset == "sikayet_tr":
        return "Şikâyetin ilgili olduğu ürün veya hizmet kategorisini metne göre sınıflandır. Şirket adına göre varsayım yapma."
    return ("Yorumun ifade ettiği genel değerlendirmeyi olumlu, olumsuz veya nötr olarak sınıflandır. Kaynak etiketler kullanıcı puanlarından türetilmiştir; yalnızca verilen metni kullan."
            if language == "tr" else
            "Classify the overall evaluation expressed by each review as positive, negative, or neutral. Source labels derive from user ratings; use only the supplied text.")


def instructions(manifest):
    cfg = manifest["config"]
    lang = cfg["language"]
    dataset = cfg.get("dataset") or cfg["out_dir"].split("/")[-1].removesuffix("_out")
    names = manifest.get("label_names", [])
    labels = (" Etiketler: " if lang == "tr" else " Labels: ") + ", ".join(names) + "." if names else ""
    numeric = (" Sayısal yanıtlarda yalnızca 0-9 rakamlarıyla tek tam sayı yaz; binlik ayıracı, yüzde işareti veya açıklama kullanma."
               if lang == "tr" else
               " For numeric answers return one integer using digits 0-9, with no thousands separator, percent sign, or explanation.")
    return task_description(dataset, lang) + labels + numeric
