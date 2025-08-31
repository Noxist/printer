# dm_data.py
# Doctrinal Mastery passages (EN + DE) as static data.
# Note: German texts use Swiss orthography (ss statt ß).

DM_PASSAGES = [
    # -------------------------
    # Old Testament
    # -------------------------
    {"ref_en": "Moses 1:39", "ref_de": "Mose 1:39",
     "en": "This is my work and my glory—to bring to pass the immortality and eternal life of man.",
     "de": "Dies ist mein Werk und meine Herrlichkeit: die Unsterblichkeit und das ewige Leben des Menschen zustande zu bringen."},

    {"ref_en": "Moses 7:18", "ref_de": "Mose 7:18",
     "en": "The Lord called his people Zion, because they were of one heart and one mind.",
     "de": "Der Herr nannte sein Volk Zion, weil es eines Herzens und eines Sinnes war."},

    {"ref_en": "Abraham 2:9–11", "ref_de": "Abraham 2:9–11",
     "en": "The Lord promised Abraham that his seed would bear this ministry and Priesthood unto all nations.",
     "de": "Der Herr verhies Abraham, dass seine Nachkommen diesen geistlichen Dienst und dieses Priestertum zu allen Nationen tragen werden."},

    {"ref_en": "Abraham 3:22–23", "ref_de": "Abraham 3:22–23",
     "en": "As spirits we were organized before the world was.",
     "de": "Unser Geist wurde geformt, ehe die Welt war."},

    {"ref_en": "Genesis 1:26–27", "ref_de": "Genesis 1:26–27",
     "en": "God created man in his own image.",
     "de": "Gott erschuf den Menschen als sein Bild, ihm ähnlich."},

    {"ref_en": "Genesis 2:24", "ref_de": "Genesis 2:24",
     "en": "A man shall cleave unto his wife: and they shall be one.",
     "de": "Der Mann hängt seiner Frau an, und sie werden ein Fleisch."},

    {"ref_en": "Genesis 39:9", "ref_de": "Genesis 39:9",
     "en": "How then can I do this great wickedness, and sin against God?",
     "de": "Wie könnte ich da ein so grosses Unrecht begehen und gegen Gott sündigen?"},

    {"ref_en": "Exodus 20:3–17", "ref_de": "Exodus 20:3–17",
     "en": "The Ten Commandments.",
     "de": "Die Zehn Gebote."},

    {"ref_en": "Joshua 24:15", "ref_de": "Josua 24:15",
     "en": "Choose you this day whom ye will serve.",
     "de": "Entscheidet euch heute, wem ihr dienen wollt."},

    {"ref_en": "Psalm 24:3–4", "ref_de": "Psalm 24:3–4",
     "en": "Who shall stand in his holy place? He that hath clean hands, and a pure heart.",
     "de": "Wer darf stehn an seiner heiligen Stätte? Der unschuldige Hände hat und ein reines Herz."},

    {"ref_en": "Proverbs 3:5–6", "ref_de": "Sprichwörter 3:5–6",
     "en": "Trust in the Lord with all thine heart … and he shall direct thy paths.",
     "de": "Mit ganzem Herzen vertrau auf den Herrn … dann ebnet er selbst deine Pfade."},

    {"ref_en": "Isaiah 1:18", "ref_de": "Jesaja 1:18",
     "en": "Though your sins be as scarlet, they shall be as white as snow.",
     "de": "Sind eure Sünden wie Scharlach, weiss wie Schnee werden sie."},

    {"ref_en": "Isaiah 5:20", "ref_de": "Jesaja 5:20",
     "en": "Woe unto them that call evil good, and good evil.",
     "de": "Wehe denen, die das Böse gut und das Gute böse nennen."},

    {"ref_en": "Isaiah 29:13–14", "ref_de": "Jesaja 29:13–14",
     "en": "The restoration of the gospel is a marvellous work and a wonder.",
     "de": "Die Wiederherstellung des Evangeliums ist wunderbar und wundersam."},

    {"ref_en": "Isaiah 53:3–5", "ref_de": "Jesaja 53:3–5",
     "en": "Surely Jesus Christ hath borne our griefs, and carried our sorrows.",
     "de": "Aber Jesus Christus hat unsere Krankheit getragen und unsere Schmerzen auf sich geladen."},

    {"ref_en": "Isaiah 58:6–7", "ref_de": "Jesaja 58:6–7",
     "en": "The blessings of a proper fast.",
     "de": "Die Segnungen, die richtiges Fasten mit sich bringt."},

    {"ref_en": "Isaiah 58:13–14", "ref_de": "Jesaja 58:13–14",
     "en": "Turn away from doing thy pleasure on my holy day; and call the sabbath a delight.",
     "de": "Halte zurück, deine Geschäfte an meinem heiligen Tag zu machen, und nenne den Sabbat eine Wonne."},

    {"ref_en": "Jeremiah 1:4–5", "ref_de": "Jeremia 1:4–5",
     "en": "Before I formed thee in the belly … I ordained thee a prophet unto the nations.",
     "de": "Noch ehe ich dich im Mutterleib formte, habe ich dich zum Propheten für die Völker bestimmt."},

    {"ref_en": "Ezekiel 3:16–17", "ref_de": "Ezechiel 3:16–17",
     "en": "The prophet is a watchman unto the house of Israel.",
     "de": "Der Prophet wurde dem Haus Israel als Wächter gegeben."},

    {"ref_en": "Ezekiel 37:15–17", "ref_de": "Ezechiel 37:15–17",
     "en": "The Bible and the Book of Mormon shall become one in thine hand.",
     "de": "Die Bibel und das Buch Mormon sollen eins werden in deiner Hand."},

    {"ref_en": "Daniel 2:44–45", "ref_de": "Daniel 2:44–45",
     "en": "God shall set up a kingdom, which shall never be destroyed.",
     "de": "Gott wird ein Reich errichten, das in Ewigkeit nicht untergeht."},

    {"ref_en": "Amos 3:7", "ref_de": "Amos 3:7",
     "en": "The Lord God revealeth his secret unto his servants the prophets.",
     "de": "Gott, der Herr, offenbart seinen Knechten, den Propheten, seinen Ratschluss."},

    {"ref_en": "Malachi 3:8–10", "ref_de": "Maleachi 3:8–10",
     "en": "The blessings of paying tithing.",
     "de": "Die Segnungen, wenn man den Zehnten zahlt."},

    {"ref_en": "Malachi 4:5–6", "ref_de": "Maleachi 3:23–24",
     "en": "Elijah shall turn the heart of the children to their fathers.",
     "de": "Elija wird das Herz der Söhne ihren Vätern zuwenden."},

    # -------------------------
    # New Testament
    # -------------------------
    {"ref_en": "Matthew 5:14–16", "ref_de": "Matthäus 5:14–16",
     "en": "Let your light so shine before men.",
     "de": "So soll euer Licht vor den Menschen leuchten."},

    {"ref_en": "Matthew 11:28–30", "ref_de": "Matthäus 11:28–30",
     "en": "Come unto me, all ye that labour and are heavy laden, and I will give you rest.",
     "de": "Kommt alle zu mir, die ihr mühselig und beladen seid! Ich will euch erquicken."},

    {"ref_en": "Matthew 16:15–19", "ref_de": "Matthäus 16:15–19",
     "en": "Jesus said, I will give unto thee the keys of the kingdom.",
     "de": "Jesus sagte: Ich werde dir die Schlüssel des Himmelreichs geben."},

    {"ref_en": "Matthew 22:36–39", "ref_de": "Matthäus 22:36–39",
     "en": "Thou shalt love the Lord thy God … Thou shalt love thy neighbour.",
     "de": "Du sollst den Herrn, deinen Gott, lieben … Du sollst deinen Nächsten lieben."},

    {"ref_en": "Luke 2:10–12", "ref_de": "Lukas 2:10–12",
     "en": "For unto you is born this day in the city of David a Saviour, which is Christ the Lord.",
     "de": "Heute ist euch in der Stadt Davids der Retter geboren; er ist der Christus, der Herr."},

    {"ref_en": "Luke 22:19–20", "ref_de": "Lukas 22:19–20",
     "en": "Jesus Christ commanded, partake of the sacrament in remembrance of me.",
     "de": "Jesus Christus gebot seinen Jüngern: Nehmt vom Abendmahl zu meinem Gedächtnis."},

    {"ref_en": "Luke 24:36–39", "ref_de": "Lukas 24:36–39",
     "en": "For a spirit hath not flesh and bones, as ye see me have.",
     "de": "Kein Geist hat Fleisch und Knochen, wie ihr es bei mir seht."},

    {"ref_en": "John 3:5", "ref_de": "Johannes 3:5",
     "en": "Except a man be born of water and of the Spirit, he cannot enter into the kingdom of God.",
     "de": "Wenn jemand nicht aus dem Wasser und dem Geist geboren wird, kann er nicht in das Reich Gottes kommen."},

    {"ref_en": "John 3:16", "ref_de": "Johannes 3:16",
     "en": "For God so loved the world, that he gave his only begotten Son.",
     "de": "Denn Gott hat die Welt so sehr geliebt, dass er seinen einzigen Sohn hingab."},

    {"ref_en": "John 7:17", "ref_de": "Johannes 7:17",
     "en": "If any man will do his will, he shall know of the doctrine.",
     "de": "Wer bereit ist, den Willen Gottes zu tun, wird erkennen."},

    {"ref_en": "John 17:3", "ref_de": "Johannes 17:3",
     "en": "And this is life eternal, that they might know thee the only true God, and Jesus Christ.",
     "de": "Das ist das ewige Leben: dass sie dich, den einzigen wahren Gott, erkennen und Jesus Christus."},

    {"ref_en": "1 Corinthians 6:19–20", "ref_de": "1 Korinther 6:19–20",
     "en": "Your body is the temple of the Holy Ghost.",
     "de": "Euer Leib ist ein Tempel des Heiligen Geistes."},

    {"ref_en": "1 Corinthians 11:11", "ref_de": "1 Korinther 11:11",
     "en": "Neither is the man without the woman, neither the woman without the man, in the Lord.",
     "de": "Im Herrn gibt es weder die Frau ohne den Mann noch den Mann ohne die Frau."},

    {"ref_en": "1 Corinthians 15:20–22", "ref_de": "1 Korinther 15:20–22",
     "en": "As in Adam all die, even so in Christ shall all be made alive.",
     "de": "Denn wie in Adam alle sterben, so werden in Christus alle lebendig gemacht werden."},

    {"ref_en": "1 Corinthians 15:40–42", "ref_de": "1 Korinther 15:40–42",
     "en": "In the Resurrection, there are three degrees of glory.",
     "de": "Bei der Auferstehung gibt es drei Grade der Herrlichkeit."},

    {"ref_en": "Ephesians 1:10", "ref_de": "Epheser 1:10",
     "en": "In the dispensation of the fulness of times he might gather together in one all things in Christ.",
     "de": "In der Fülle der Zeiten wird Gott in Christus alles vereinen."},

    {"ref_en": "Ephesians 2:19–20", "ref_de": "Epheser 2:19–20",
     "en": "The Church is built upon the foundation of the apostles and prophets, Jesus Christ himself being the chief corner stone.",
     "de": "Die Kirche ist auf das Fundament der Apostel und Propheten gebaut; der Eckstein ist Christus Jesus selbst."},

    {"ref_en": "2 Thessalonians 2:1–3", "ref_de": "2 Thessalonicher 2:1–3",
     "en": "The day of Christ shall not come, except there come a falling away first.",
     "de": "Vor dem Tag des Herrn muss zuerst der Abfall von Gott kommen."},

    {"ref_en": "2 Timothy 3:15–17", "ref_de": "2 Timotheus 3:15–17",
     "en": "The holy scriptures are able to make thee wise unto salvation.",
     "de": "Die heiligen Schriften können dich weise machen zum Heil."},

    {"ref_en": "Hebrews 12:9", "ref_de": "Hebräer 12:9",
     "en": "Heavenly Father is the Father of spirits.",
     "de": "Der Vater im Himmel ist der Vater der Geister."},

    {"ref_en": "James 1:5–6", "ref_de": "Jakobus 1:5–6",
     "en": "If any of you lack wisdom, let him ask of God.",
     "de": "Fehlt es einem von euch an Weisheit, dann soll er sie von Gott erbitten."},

    {"ref_en": "James 2:17–18", "ref_de": "Jakobus 2:17–18",
     "en": "Faith, if it hath not works, is dead.",
     "de": "So ist auch der Glaube für sich allein tot, wenn er nicht Werke vorzuweisen hat."},

    {"ref_en": "1 Peter 4:6", "ref_de": "1 Petrus 4:6",
     "en": "The gospel was preached also to them that are dead.",
     "de": "Denn auch Toten ist das Evangelium verkündet worden."},

    {"ref_en": "Revelation 20:12", "ref_de": "Offenbarung 20:12",
     "en": "And the dead were judged according to their works.",
     "de": "Die Toten wurden gerichtet nach ihren Taten."},

    # -------------------------
    # Book of Mormon
    # -------------------------
    {"ref_en": "1 Nephi 3:7", "ref_de": "1 Nephi 3:7",
     "en": "I will go and do the things which the Lord hath commanded.",
     "de": "Ich will hingehen und das tun, was der Herr geboten hat."},

    {"ref_en": "2 Nephi 2:25", "ref_de": "2 Nephi 2:25",
     "en": "Adam fell that men might be; and men are, that they might have joy.",
     "de": "Adam fiel, damit Menschen sein können; und Menschen sind, damit sie Freude haben können."},

    {"ref_en": "2 Nephi 2:27", "ref_de": "2 Nephi 2:27",
     "en": "They are free to choose liberty and eternal life … or captivity and death.",
     "de": "Es steht ihnen frei, Freiheit und ewiges Leben … oder Gefangenschaft und Tod zu wählen."},

    {"ref_en": "2 Nephi 26:33", "ref_de": "2 Nephi 26:33",
     "en": "All are alike unto God.",
     "de": "Alle sind vor Gott gleich."},

    {"ref_en": "2 Nephi 28:30", "ref_de": "2 Nephi 28:30",
     "en": "God will give unto the children of men line upon line, precept upon precept.",
     "de": "Gott wird den Menschenkindern Zeile um Zeile geben, Weisung um Weisung."},

    {"ref_en": "2 Nephi 32:3", "ref_de": "2 Nephi 32:3",
     "en": "Feast upon the words of Christ; for behold, the words of Christ will tell you all things what ye should do.",
     "de": "Weidet euch an den Worten von Christus; denn siehe, die Worte von Christus werden euch alles sagen, was ihr tun sollt."},

    {"ref_en": "2 Nephi 32:8–9", "ref_de": "2 Nephi 32:8–9",
     "en": "Ye must pray always.",
     "de": "Ihr müsst immer beten."},

    {"ref_en": "Mosiah 2:17", "ref_de": "Mosia 2:17",
     "en": "When ye are in the service of your fellow beings ye are only in the service of your God.",
     "de": "Wenn ihr euren Mitmenschen dient, dann dient ihr eurem Gott."},

    {"ref_en": "Mosiah 2:41", "ref_de": "Mosia 2:41",
     "en": "Those that keep the commandments of God are blessed in all things.",
     "de": "Diejenigen, die die Gebote Gottes halten, sind gesegnet in allem."},

    {"ref_en": "Mosiah 3:19", "ref_de": "Mosia 3:19",
     "en": "Put off the natural man and become a saint through the atonement of Christ the Lord.",
     "de": "Legt den natürlichen Menschen ab und werdet durch das Sühnopfer Christi, des Herrn, ein Heiliger."},

    {"ref_en": "Mosiah 4:9", "ref_de": "Mosia 4:9",
     "en": "Believe in God; believe that he has all wisdom.",
     "de": "Glaubt an Gott; glaubt daran, dass er alle Weisheit hat."},

    {"ref_en": "Mosiah 18:8–10", "ref_de": "Mosia 18:8–10",
     "en": "Be baptized in the name of the Lord, as a witness that ye have entered into a covenant with him.",
     "de": "Lasst euch im Namen des Herrn taufen zum Zeugnis, dass ihr mit ihm den Bund eingegangen seid."},

    {"ref_en": "Alma 7:11–13", "ref_de": "Alma 7:11–13",
     "en": "And he shall go forth, suffering pains and afflictions and temptations of every kind.",
     "de": "Und er wird hingehen und Schmerzen und Bedrängnisse und Versuchungen jeder Art leiden."},

    {"ref_en": "Alma 34:9–10", "ref_de": "Alma 34:9–10",
     "en": "There must be an atonement made, an infinite and eternal sacrifice.",
     "de": "Es muss ein Sühnopfer vollbracht werden, ein unbegrenztes und ewiges Opfer."},

    {"ref_en": "Alma 39:9", "ref_de": "Alma 39:9",
     "en": "Go no more after the lusts of your eyes.",
     "de": "Folge nicht mehr der Begierde deiner Augen."},

    {"ref_en": "Alma 41:10", "ref_de": "Alma 41:10",
     "en": "Wickedness never was happiness.",
     "de": "Schlecht zu sein hat noch nie glücklich gemacht."},

    {"ref_en": "Helaman 5:12", "ref_de": "Helaman 5:12",
     "en": "It is upon the rock of our Redeemer that ye must build your foundation.",
     "de": "Unser Erlöser ist der Fels, auf dem ihr eure Grundlage bauen müsst."},

    {"ref_en": "3 Nephi 11:10–11", "ref_de": "3 Nephi 11:10–11",
     "en": "I have suffered the will of the Father in all things from the beginning.",
     "de": "Ich habe den Willen des Vaters in allem von Anfang an gelitten."},

    {"ref_en": "3 Nephi 12:48", "ref_de": "3 Nephi 12:48",
     "en": "Be perfect even as I, or your Father who is in heaven is perfect.",
     "de": "Seid vollkommen, so wie ich oder euer Vater, der im Himmel ist, vollkommen ist."},

    {"ref_en": "3 Nephi 27:20", "ref_de": "3 Nephi 27:20",
     "en": "Come unto me and be baptized … that ye may be sanctified by the reception of the Holy Ghost.",
     "de": "Kommt zu mir und lasst euch taufen, damit ihr durch den Empfang des Heiligen Geistes geheiligt werdet."},

    {"ref_en": "Ether 12:6", "ref_de": "Ether 12:6",
     "en": "Ye receive no witness until after the trial of your faith.",
     "de": "Ein Zeugnis empfangt ihr erst, nachdem euer Glaube geprüft ist."},

    {"ref_en": "Ether 12:27", "ref_de": "Ether 12:27",
     "en": "If men come unto me … then will I make weak things become strong unto them.",
     "de": "Wenn Menschen zu mir kommen, werde ich Schwaches für sie stark werden lassen."},

    {"ref_en": "Moroni 7:45–48", "ref_de": "Moroni 7:45–48",
     "en": "Charity is the pure love of Christ.",
     "de": "Nächstenliebe ist die reine Christusliebe."},

    {"ref_en": "Moroni 10:4–5", "ref_de": "Moroni 10:4–5",
     "en": "Ask with a sincere heart, with real intent, having faith in Christ … and by the power of the Holy Ghost ye may know the truth of all things.",
     "de": "Fragt mit aufrichtigem Herzen, mit wirklichem Vorsatz und habt Glauben an Christus. Und durch die Macht des Heiligen Geistes könnt ihr von allem wissen, ob es wahr ist."},

    # -------------------------
    # Doctrine & Covenants / Church History
    # -------------------------
    {"ref_en": "Joseph Smith—History 1:15–20", "ref_de": "Joseph Smith – Lebensgeschichte 1:15–20",
     "en": "Joseph Smith saw two Personages, whose brightness and glory defy all description.",
     "de": "Joseph Smith sah zwei Personen von unbeschreiblicher Helle und Herrlichkeit."},

    {"ref_en": "D&C 1:30", "ref_de": "LuB 1:30",
     "en": "The only true and living church.",
     "de": "Die einzige wahre und lebendige Kirche."},

    {"ref_en": "D&C 1:37–38", "ref_de": "LuB 1:37–38",
     "en": "Whether by mine own voice or by the voice of my servants, it is the same.",
     "de": "Sei es durch meine eigene Stimme oder durch die Stimme meiner Diener, das ist dasselbe."},

    {"ref_en": "D&C 6:36", "ref_de": "LuB 6:36",
     "en": "Look unto me in every thought; doubt not, fear not.",
     "de": "Blickt in jedem Gedanken auf mich; zweifelt nicht, fürchtet euch nicht."},

    {"ref_en": "D&C 8:2–3", "ref_de": "LuB 8:2–3",
     "en": "I will tell you in your mind and in your heart, by the Holy Ghost.",
     "de": "Ich werde es dir in deinem Verstand und in deinem Herzen durch den Heiligen Geist sagen."},

    {"ref_en": "D&C 13:1", "ref_de": "LuB 13:1",
     "en": "The Aaronic Priesthood holds the keys of the ministering of angels, and of the gospel of repentance, and of baptism.",
     "de": "Das Aaronische Priestertum hat die Schlüssel des Dienstes von Engeln und die des Evangeliums der Umkehr und die der Taufe inne."},

    {"ref_en": "D&C 18:10–11", "ref_de": "LuB 18:10–11",
     "en": "The worth of souls is great in the sight of God.",
     "de": "Die Seelen haben grossen Wert in den Augen Gottes."},

    {"ref_en": "D&C 18:15–16", "ref_de": "LuB 18:15–16",
     "en": "How great will be your joy if you should bring many souls unto me!",
     "de": "Wie gross wird eure Freude sein, wenn ihr viele Seelen zu mir führt!"},

    {"ref_en": "D&C 19:16–19", "ref_de": "LuB 19:16–19",
     "en": "I, Jesus Christ, have suffered these things for all.",
     "de": "Ich, Jesus Christus, habe das für alle gelitten."},

    {"ref_en": "D&C 21:4–6", "ref_de": "LuB 21:4–6",
     "en": "The prophet’s word ye shall receive, as if from mine own mouth.",
     "de": "Das Wort des Propheten sollt ihr empfangen, als sei es aus meinem eigenen Mund."},

    {"ref_en": "D&C 29:10–11", "ref_de": "LuB 29:10–11",
     "en": "I will reveal myself from heaven with power and great glory … and dwell in righteousness with men on earth a thousand years.",
     "de": "Ich werde mich vom Himmel her mit Macht und grosser Herrlichkeit offenbaren und in Rechtschaffenheit eintausend Jahre bei den Menschen auf Erden wohnen."},

    {"ref_en": "D&C 49:15–17", "ref_de": "LuB 49:15–17",
     "en": "Marriage is ordained of God.",
     "de": "Die Ehe ist von Gott verordnet."},

    {"ref_en": "D&C 58:42–43", "ref_de": "LuB 58:42–43",
     "en": "He who has repented of his sins, the same is forgiven.",
     "de": "Wer von seinen Sünden umgekehrt ist, dem ist vergeben."},

    {"ref_en": "D&C 64:9–11", "ref_de": "LuB 64:9–11",
     "en": "Of you it is required to forgive all men.",
     "de": "Von euch wird verlangt, dass ihr allen Menschen vergebt."},

    {"ref_en": "D&C 76:22–24", "ref_de": "LuB 76:22–24",
     "en": "By Jesus Christ the worlds are and were created.",
     "de": "Von Jesus Christus werden und wurden die Welten erschaffen."},

    {"ref_en": "D&C 82:10", "ref_de": "LuB 82:10",
     "en": "I, the Lord, am bound when ye do what I say.",
     "de": "Ich, der Herr, bin verpflichtet, wenn ihr tut, was ich sage."},

    {"ref_en": "D&C 84:20–22", "ref_de": "LuB 84:20–22",
     "en": "In the ordinances thereof, the power of godliness is manifest.",
     "de": "Darum wird in seinen Verordnungen die Macht des Göttlichen kundgetan."},

    {"ref_en": "D&C 88:118", "ref_de": "LuB 88:118",
     "en": "Seek learning, even by study and also by faith.",
     "de": "Trachtet nach Wissen, ja, durch Studium und auch durch Glauben."},

    {"ref_en": "D&C 89:18–21", "ref_de": "LuB 89:18–21",
     "en": "The blessings of the Word of Wisdom.",
     "de": "Die Segnungen, die auf dem Wort der Weisheit beruhen."},

    {"ref_en": "D&C 107:8", "ref_de": "LuB 107:8",
     "en": "The Melchizedek Priesthood has power and authority to administer in spiritual things.",
     "de": "Das Melchisedekische Priestertum hat Macht und Vollmacht, um in geistigen Belangen zu amtieren."},

    {"ref_en": "D&C 121:36, 41–42", "ref_de": "LuB 121:36, 41–42",
     "en": "The rights of the priesthood cannot be controlled nor handled only on the principles of righteousness.",
     "de": "Die Rechte des Priestertums können nur nach den Grundsätzen der Rechtschaffenheit beherrscht und gebraucht werden."},

    {"ref_en": "D&C 130:22–23", "ref_de": "LuB 130:22–23",
     "en": "The Father has a body of flesh and bones; the Son also; but the Holy Ghost is a personage of Spirit.",
     "de": "Der Vater hat einen Körper aus Fleisch und Gebein, ebenso der Sohn; aber der Heilige Geist ist eine Person aus Geist."},

    {"ref_en": "D&C 131:1–4", "ref_de": "LuB 131:1–4",
     "en": "The new and everlasting covenant of marriage.",
     "de": "Der neue und immerwährende Bund der Ehe."},

    {"ref_en": "D&C 135:3", "ref_de": "LuB 135:3",
     "en": "Joseph Smith brought forth the Book of Mormon, which he translated by the gift and power of God.",
     "de": "Joseph Smith hat das Buch Mormon hervorgebracht, das er durch die Gabe und Macht Gottes übersetzte."},
]
