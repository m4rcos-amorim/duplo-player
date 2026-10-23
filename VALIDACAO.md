# Validação — 4 de outubro de 2026

Projeto: Duplo Player. Windows 11 de 64 bits; Python 3.11;
PySide6 6.11.2; LibVLC 3.0.24; PyInstaller 6.22.3.

## Resultados

- **9 testes unitários aprovados**: lista, aleatório sem repetição no ciclo,
  fim da lista, repetir vídeo/lista, histórico, remoção de itens e validação A–B.
- **25 verificações de integração aprovadas** com o VLC real.
  Vídeos e áudio são sintéticos, criados exclusivamente para o teste.
- Reprodução validada em MP4/H.264, MKV, AVI/MPEG-4, MOV, WebM/VP9,
  WMV, MPEG-2, TS, FLV, MP4/HEVC e MKV/AV1.
- Proporções corretas verificadas em 960×540 e 320×180, inclusive MPEG/TS.
- Mesma imagem QImage nas duas perspectivas em 20 amostras de reprodução.
- Seleção por eventos reais de mouse, recortes independentes, rejeição de
  seleção fora do quadro e restauração de somente uma perspectiva.
- Pausa, avanço de quadro e retomada; câmera lenta 0,25× com avanço de
  aproximadamente 250 ms de mídia em 1,2 s após estabilizar a busca.
- A–B retornou a A duas vezes durante a amostragem; repetição de vídeo,
  avanço da lista e retorno ao começo no modo repetir lista aprovados.
- Comando do Explorer conferido por mock; a janela do Explorer não foi automatizada.
- Confirmação cancelada: arquivo preservado e reprodução retomada.
- Falha simulada de reciclagem: arquivo preservado e reprodução retomada.
- Envio real à lixeira aprovado usando uma cópia descartável criada em
  `test-output`, sem alterar o vídeo sintético de origem ou vídeos pessoais.
- **Executável portátil aprovado**: inicializa sem Python externo, decodifica
  o vídeo, divide a tela, aplica zooms diferentes, aceita velocidade 0,5×,
  inicializa a API COM da lixeira e encerra com código 0.

## Evidências

- `test-output/integration-results.json` e `integration.log`.
- `test-output/duas-perspectivas.png` e `player-inicial.png`.
- `test-output/packaged-smoke/packaged-smoke.json` e `player-preview.png`.

O pacote foi revisado visualmente com as fontes instaladas do Windows.
A compilação isola a busca de DLLs do PATH de outros programas e usa a ICU
nativa do Windows. Nenhuma biblioteca do sistema foi instalada ou substituída.

## Limites da validação

Os testes usam arquivos sintéticos de curta duração. Não certificam todos os
perfis de codec nem desempenho em vídeos 4K/8K. A sincronização das perspectivas
é garantida pelo compartilhamento do mesmo quadro. A precisão da busca/A–B
continua dependendo do codec e dos quadros-chave. Reprodução de áudio real não
foi avaliada por escuta. DRM não é suportado.


## Atualização: interface e atalhos

- 14 testes aprovados: os 9 testes do modelo e 5 testes da interface.
- Lista oculta ao abrir; opção Ctrl+L disponível somente no modo janela.
- Tela cheia exibe somente vídeo, sem controles, títulos, bordas ou margens.
- Divisão e zooms independentes preservados ao entrar/sair da tela cheia.
- F11, Esc, D e Z verificados por eventos reais de teclado.
- Setas retrocedem/avançam 5 segundos mesmo com foco no volume ou velocidade.
- 1/2 navegam para vídeo anterior/próximo no modo janela e em tela cheia.
- Captura de interface: test-output/fullscreen-ui.png.
- O teste do executável também verifica tela cheia dividida, ausência de
  controles/lista e preservação dos zooms ao retornar ao modo janela.


## Atualização: Ctrl+S e repetição pela tecla 3

- 17 testes aprovados: modelo e interface.
- Ctrl+S ativa/desativa a seleção de zoom sem acionar o atalho S de parar.
- Arraste do mouse em tela cheia dividida amplia cada perspectiva separadamente,
  preservando a tela cheia e mantendo os controles ocultos.
- Tecla 3 marca A no primeiro toque e B no segundo; um novo toque inicia outro
  trecho. C limpa A–B. Intervalos menores que 0,1 s são recusados sem perder A.
- Os atalhos foram verificados no modo janela e em tela cheia, inclusive com
  foco no controle de velocidade. Tecla 3 sem vídeo não altera os marcadores.
- O teste do executável também simula Ctrl+S/arraste em tela cheia e dois toques
  em 3 durante a reprodução de um vídeo sintético.

## Atualização: Ctrl+D

- Ctrl+D alterna uma/duas telas no modo janela e em tela cheia.
- Alternância mantém os zooms de cada perspectiva e não sai da tela cheia.
- 17 testes aprovados; diagnóstico do executável verifica o novo atalho.


## Atualização: controles inferiores, Ctrl+Z, modos e gravação

- 26 testes de modelo/interface/PCM aprovados e 25 verificações reais de reprodução.
- Todos os botões estão no painel inferior, com ícones e dicas de atalhos.
- Repetir o vídeo conserva a divisão e ambos os recortes; verificado com VLC real.
- Ctrl+Z restaura apenas a perspectiva selecionada, inclusive em tela cheia.
- Ordem sequencial/sorteio por vídeo/lista embaralhada e repetição são independentes.
- Gravação real de MP4: duas telas com zoom, câmera lenta, pausa, troca para tela
  cheia e uma segunda gravação. Pixels do MP4 decodificado comparados com a
  composição de origem, áudio decodificado com energia RMS verificada.
- Resultado: test-output/recording/results.json. Gravação padrão em C:\Videos.
- O diagnóstico do executável grava um vídeo sintético na pasta padrão e verifica
  os atalhos, os recortes e a finalização do arquivo com vídeo e áudio.

## Correção: abrir local do vídeo

- A seleção usa SHParseDisplayName/SHOpenFolderAndSelectItems com a pasta e
  o arquivo separados, em vez de argumentos de texto para explorer.exe.
- O botão usa o arquivo reproduzido mesmo se a posição da lista for diferente.
- Arquivo movido/renomeado e falha do Shell geram mensagens claras.
- Inicialização COM balanceada pelas funções do Windows preserva o estado do
  chamador em chamadas repetidas; teste de regressão incluído.
- 32 testes de modelo/interface/áudio/Explorer aprovados.
- Integração real confirma pasta e seleção exata em quatro situações: acentos,
  espaços, vírgulas e símbolos; vírgulas sem espaços; nomes iguais em pastas
  diferentes; reutilização da primeira pasta. Resultados de fonte e executável:
  test-output/explorer-cases/source-results.json e packaged-results.json.

## Correção: volume inicial e troca de vídeo

- Reproduzida a falha anterior: PCM com a mesma energia para volume 100 e 10;
  pedidos de volume antes da saída VLC existir retornavam falha.
- A barra controla diretamente QAudioSink. Seu ganho é aplicado antes de iniciar
  a saída e após cada reinicialização, sem depender do estado assíncrono do VLC.
- Volume restaurado ao abrir, silêncio, troca de arquivo, repetição e busca
  mantêm o ganho escolhido. O callback de volume do VLC não altera esse estado.
- Gravação usa PCM original com histórico do ganho da reprodução; mudanças
  de volume/silêncio são aplicadas ao instante correto das amostras.
- 38 testes automatizados aprovados. Teste com VLC e saída Qt reais confirmou
  início em 7%, repetição/troca em 7%, silêncio preservado, retorno em 3% e zero.
  Energia PCM da gravação confirmou esses ganhos; test-output/volume-results.json.
- Integração de gravação MP4 aprovada, incluindo áudio, pausa, câmera lenta,
  zoom duplo, tela cheia e finalização ao fechar.
- Diagnóstico do executável verifica saída inicial em 7% e alternância de silêncio.
  Diagnósticos não sobrescrevem as preferências salvas do usuário.

## Atalho - para câmera lenta

- Tecla - aplica 0,75×, depois 0,5× e 0,25×; novos toques mantêm 0,25×.
- Funciona também em tela cheia, com foco no volume/velocidade e no teclado numérico.
- Repetição automática ao segurar a tecla desativada: uma etapa por toque.
- Ajuda F1, dica de velocidade e README atualizados.
- 39 testes automatizados aprovados. Diagnóstico do executável verifica velocidade
  real do VLC, o limite, tela cheia e o teclado numérico.

## Atalho + para recuperar e aumentar velocidade

- Tecla + aumenta em etapas: 0,25×, 0,5×, 0,75×, 1×, 1,25×, 1,5× e 2×.
- A partir de 2×, novos toques mantêm o limite. Uma etapa por toque.
- Funciona em tela cheia, com foco nos controles, no teclado numérico e com Shift
  para digitar o sinal + no teclado principal.
- Ajuda F1, dica de velocidade e README atualizados. 40 testes aprovados.
- Diagnóstico do executável verifica recuperação da câmera lenta, velocidade
  normal e aceleração até 2× com o VLC real, inclusive em tela cheia.

## Ctrl+R: rotação independente por perspectiva

- Ctrl+R gira a tela selecionada 90° no sentido horário: 0°, 90°, 180°, 270°, 0°.
- Ícone no painel inferior, menu da imagem e ajuda F1 incluídos.
- Funcionamento em janela/tela cheia; Ctrl+Z restaura só o zoom, mantendo rotação.
- Proporção preservada. Seleções feitas sobre a imagem girada são convertidas
  para o recorte da imagem original, inclusive em zooms sucessivos.
- Repetição conserva as rotações de ambas as telas e os recortes.
- Tela e gravação compartilham a mesma função de desenho, sem girar/copiar o
  quadro decodificado e sem alterar a sincronia entre perspectivas.
- 43 testes aprovados. Quadrantes coloridos conferem o sentido horário, todos
  os ângulos, proporção, independência entre telas e pixels da composição gravada.
- MP4 real com telas a 90°/270°, zoom, câmera lenta, pausa e tela cheia aprovado:
  pixels decodificados comparados com a composição, erro médio 7,59/255.
  Resultados em test-output/recording/results.json.
- Diagnóstico do executável verifica ciclo completo e rotação independente em
  tela cheia e gravação em C:\Videos.

## Supressão de ruído em tempo real

- Ícone liga/desliga no painel inferior, níveis Suave/Médio/Forte, Ctrl+H e
  menu da imagem em tela cheia. Preferência de ativação/intensidade persistida.
- Filtro espectral adaptativo estéreo em janelas sobrepostas de 1024 amostras,
  FFT vetorizada e ganho compartilhado entre canais. Antecipação de 512 amostras
  compensada pelos timestamps originais; duração e alinhamento preservados.
- Áudio original/filtrado mantido em buffers limitados. Mudanças de intensidade
  seguem o instante da reprodução e da gravação. Busca/repetição reinicia o
  estimador e descarta áudio futuro, preservando amostras já usadas na gravação.
- 52 testes aprovados: redução progressiva, preservação do sinal principal,
  duração exata com blocos irregulares, estéreo, silêncio, finalização, busca,
  transições entre níveis, tela cheia e restauração das preferências.
- VLC real: proporção RMS do ruído 0,728/0,480/0,174 nos níveis suave/médio/forte.
  Sinal de 1 kHz preservou 94,9% da energia RMS em cenário de ruído + sinal.
  MP4 AAC gravado e decodificado confirmou redução de ruído. Busca, câmera lenta
  e desativação conferidas; test-output/noise/results.json.
- Gravação com supressão forte, zoom duplo, rotações 90°/270°, câmera lenta,
  pausa e tela cheia aprovada; test-output/recording/results.json.
- Diagnóstico do executável verifica Ctrl+H em tela cheia, dados filtrados
  usados na gravação e a distribuição de NumPy no aplicativo.


## Supressão ajustável de 0 a 100% — 06/10/2026

- Barra na aba inferior com porcentagem visível e ajuste em passos de 1%.
- A mesma barra está disponível no menu do botão direito em tela cheia.
- 0% preserva o PCM original; 100% usa o filtro completo. Valores intermediários
  misturam o áudio original com o filtrado, sem alterar o volume principal.
- Reprodução e gravação usam a mesma intensidade em cada instante.
- Porcentagem salva ao fechar; níveis antigos migrados para 35%, 65% e 100%.
- 54 testes passaram, incluindo todos os 101 valores e mudanças no meio do PCM.
- Integração com VLC e MP4/AAC passou em 35%, 65% e 100%, incluindo câmera lenta,
  busca e retorno ao áudio original ao desligar.


## Preferências e vídeos arrastados — 16/10/2026

- Ordem sequencial/aleatório vídeo/aleatório lista e repetição desligada/vídeo/lista
  são restauradas com os respectivos ícones; tela dupla, volume e silêncio também.
- O supressor começa desligado em cada abertura, inclusive após fechar com ele
  ligado. A porcentagem escolhida continua salva.
- Arrastar vídeos executa imediatamente o primeiro válido, incluindo vídeos já
  presentes na lista e arrastos com outro arquivo em reprodução.
- 57 testes passaram: combinações de ordem e repetição, modos inválidos, volume,
  tela dupla, supressor desligado e arrasto de vários vídeos sem duplicatas.
- tests/preferences_integration.py passou com QSettings em arquivo INI real,
  reabertura da janela e eventos Qt de arrasto alternando MP4 e HEVC via VLC.
  Resultado: test-output/preferences-drop/results.json.


## Idiomas da interface — 21/10/2026 (inglês e português do Brasil)

O que mudou: todos os textos visíveis ao usuário foram para `duplo/i18n.py`, em pares português / inglês
(janela, botões, dicas, barra de status, diálogos, menu do botão direito, ajuda F1, tela inicial e mensagens
de erro). Os nomes de `Repeat` e `PlaybackOrder` exibidos ao usuário agora vêm de `.label`; o `.value` virou um
identificador estável. As preferências salvas usam o nome do enum e não são afetadas.

O que foi conferido, fora do Windows, com o motor VLC simulado:

- `tests/test_i18n.py` (11 testes novos) passou: os dois idiomas existem para cada chave, com os mesmos
  campos; nenhum texto em inglês tem acento do português; a ajuda F1 tem o mesmo número de linhas; ordem
  `DUPLO_LANG` / preferência salva / idioma do sistema; os nomes de enum seguem o idioma; a janela em inglês
  não mostra português em rótulos, dicas e nomes acessíveis; escolher um idioma o salva uma única vez.
- Uma checagem estática confirmou que toda chamada `tr(...)` usa uma chave existente com os campos certos.

Rodado no Windows 11 Pro (10.0.26200), Python 3.11, VLC 3.0.24 — 21/10/2026:

- `i18n.system_language()` retornou `pt` nesta máquina.
- `python -m unittest discover -s tests -v`: 68 testes, 0 falhas, 0 erros (27 em `test_ui.py`, 11 em `test_i18n.py`).
- Scripts de integração com o VLC real, um por vez: `noise_integration.py`, `volume_integration.py`,
  `preferences_integration.py` e `explorer_integration.py` passaram. Os vídeos de teste foram criados com
  `make_fixture` do `integration.py`, sem rodar o `main()` desse script.
- `integration.py` (envia uma cópia descartável para a lixeira real do Windows): a primeira execução parou na
  verificação do laço A–B com 1 volta ao ponto A em vez de pelo menos 2, depois de 16 verificações; a execução
  seguinte, sem mudanças, passou nas 25 verificações (3 voltas a A), inclusive nos botões de diálogo clicados
  por `tr(...)`. Mais duas execuções, sem mudanças, pararam na mesma verificação do A–B (1 volta a A, depois de
  16 verificações): 1 dessas 3 execuções passou nas 25 verificações (4 execuções no total: 1 passou, 3 pararam
  no A–B). O teste não foi alterado.
- Causa das falhas do A–B, encontrada rastreando o teste sem alterá-lo: a verificação roda no último vídeo de
  formatos, `teste_av1.mkv` (2 s), e o B muitas vezes caía cerca de 80 ms antes do fim do arquivo. O VLC informa
  o tempo em saltos de cerca de 250–300 ms, então o arquivo terminava antes de um tempo ≥ B ser informado. O
  caminho de fim de arquivo do app recarregava o arquivo e chamava `_restore_position(A)`, mas a busca era
  enviada com a mídia ainda abrindo; o VLC a ignorava e a reprodução recomeçava do 0, não de A.
- Correção em `duplo/window.py`: `_restore_position` agora espera o player estar em `Playing` (e aceitar
  busca) antes de buscar, tentando de novo a cada 100 ms como antes. Isso também vale para a restauração da
  posição depois de uma falha da lixeira. Depois da correção: 68 testes unitários passaram; `integration.py`
  passou nas 25 verificações em 4 de 4 execuções (3, 2, 2 e 2 voltas a A; o teste exige pelo menos 2);
  `recording_integration.py`, `volume_integration.py`, `noise_integration.py`, `preferences_integration.py` e
  `explorer_integration.py` passaram.
- `recording_integration.py` passou (grava em `test-output\recording`, não em `C:\Videos`): MP4 composto
  1268×644, 3,53 s, supressão de ruído em 100, zoom duplo, rotações 90/270, câmera lenta, pausa, tela cheia,
  segunda gravação e finalização ao fechar.
- Janela capturada em modo offscreen em inglês e em português: nenhum texto cortado ou sobreposto, e nenhum
  texto em português na janela em inglês.
- App real (`main.py`) aberto com um vídeo sintético: com `DUPLO_LANG=en` e `DUPLO_LANG=pt`, os rótulos, a
  barra de status, a ajuda F1 e o menu do botão direito apareceram no idioma escolhido. Escolher um idioma em
  "Idioma / Language" gravou `language` num `QSettings` INI temporário; sem `DUPLO_LANG`, a abertura seguinte
  usou o valor salvo (`en`, depois `pt`).
- O `build.ps1` gerou `dist\DuploPlayer\DuploPlayer.exe` com os oito documentos. O `installer.ps1` gerou o
  instalador; a instalação silenciosa (`/VERYSILENT`) numa pasta temporária terminou sem janela de idioma, o
  app instalado passou no `--smoke-test` com `DUPLO_LANG=en` (VLC 3.0.24, 76 quadros gravados, supressão de
  ruído em 100) e a desinstalação silenciosa removeu os arquivos e o atalho do Menu Iniciar.

## Barra de tempo flutuante em tela cheia e junção de trechos gravados — 22/10/2026

- Em tela cheia, uma barra de tempo flutuante (busca e tempo) aparece sobre a parte de baixo do vídeo enquanto
  o mouse está a até 90 px da borda inferior ou arrastando a barra; ela some quando o mouse sai. Ela é filha
  da janela, não das perspectivas, por isso nunca entra na gravação.
- Ctrl+G continua gravando um MP4 por início/fim. Ctrl+Shift+G (botão e menu do botão direito) junta os
  trechos gravados desde a última junção, em ordem, por cópia de fluxo no FFmpeg (sem recodificar). Os trechos
  seguintes usam o tamanho do primeiro. Após juntar com sucesso, os trechos vão para a lixeira; em caso de
  falha, são mantidos.
- 71 testes unitários aprovados (3 novos: a barra aparece/some conforme a zona do cursor e sai junto com a
  tela cheia; clicar nela faz a busca; juntar exige dois trechos). `integration.py` passou nas 25 verificações;
  `recording_integration.py` passou.
- Novo `segments_integration.py` aprovado com VLC e FFmpeg reais (em `test-output\segments`, com a lixeira
  simulada): 3 trechos de 1,03, 1,23 e 0,83 s gravados em janela, tela cheia e tela dividida, todos 1268×644,
  unidos em um MP4 de 3,12 s com áudio AAC, decodificado sem erros; Ctrl+Shift+G durante a gravação
  finalizou aquele trecho e juntou 2 trechos.
