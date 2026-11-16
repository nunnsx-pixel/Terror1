# Falas do roteiro: id -> (voz, texto, rate%, pitch_st)  (pitch em semitons aplicado depois via rubberband)
ANT, FRA = "pt-BR-AntonioNeural", "pt-BR-FranciscaNeural"
LINES = {
 # ---------------- PARTE 1 ----------------
 "p1_whisper": (ANT, "Eles sabiam que vocês iam voltar...", -10, -5),
 "p1_lucas1":  (ANT, "Caralho! Clara, tu viu isso?! Tem alguém correndo atrás da gente nesse corredor!", 38, -0.5),
 "p1_clara1":  (FRA, "Lucas, eu te falei para a gente não entrar nesse Bloco C! Os relatórios da internet diziam que esse lugar foi isolado em 1994 porque os pacientes sumiam de dentro das celas trancadas por dentro! Vamos embora agora, por favor!", 34, 0.5),
 "p1_marcos1": (ANT, "Para com isso, Clara, isso é só marketing de lenda urbana para assustar vândalo... Pera. Olha pro chão.", 26, -2.5),
 "p1_lucas2":  (ANT, "O que foi?", 5, -0.5),
 "p1_marcos2": (ANT, "Por que tem pegadas frescas de lama e barro no chão seco, se a gente acabou de arrombar a porta da frente e foi o primeiro grupo a pisar aqui em trinta anos?", 30, -2.5),
 "p1_lucas3":  (ANT, "Galera... olha isso aqui. Se o cadeado estava trancado perfeitamente por fora, como é que arrombaram desse jeito? E olha o sangue seco no trinco...", 28, -0.5),
 "p1_marcos3": (ANT, "Isso não faz o menor sentido físico... Não tem outra janela, não tem duto de ventilação. É um beco sem saída absoluto.", 28, -2.5),
 # ---------------- PARTE 2 ----------------
 "p2_lucas1":  (ANT, "A live caiu do ar... Não tem mais sinal de rede nenhum, nada. A gente tá preso a três andares abaixo do nível da rua, no escuro total.", 32, -0.5),
 "p2_clara1":  (FRA, "Lucas... o Marcos foi checar o corredor lateral há dois minutos para ver se achava uma saída de ar. Por que ele não tá respondendo às chamadas?", 28, 0.5),
 "p2_lucas2":  (ANT, "Marcos? Cara, vira aqui agora! Chega dessa brincadeira, a bateria do celular tá morrendo, vamos vazar daqui!", 22, -0.5),
 "p2_marcos1": (ANT, "Eles não deixam a gente subir... Quem desce para o subsolo, vira parte da fundação para sempre.", -4, -6),
 "p2_lucas3":  (ANT, "Abre! Abre essa merda! Socorro! Alguém abre!", 24, 0.5),
 "p2_clara2":  (FRA, "Não tem saída, Lucas! Eles trancaram a gente!", 20, 1.5),
 "p2_final":   (ANT, "Obrigado por registrarem a nossa história... A porta da sua casa agora está aberta.", -8, -4),
}
