# Segurança: como verificar o Duplo Player

Versão em inglês: [SECURITY.md](SECURITY.md).

Se você desconfia de baixar um `.exe` da internet, faz bem. Este guia mostra como conferir o
instalador por conta própria, sem precisar confiar em mim. Os passos vão do mais rápido ao mais completo.

## O que foi verificado

O SHA256 e o relatório do VirusTotal de cada instalador ficam publicados nas **notas da sua Release**, e não
neste arquivo. O hash muda a cada build e este arquivo vai dentro do instalador, então ele não pode conter o hash
do arquivo que o carrega. As notas da Release também dizem quando a análise foi feita.

| Item | Onde ver |
|---|---|
| SHA256 do instalador | Notas da Release (e Passo 1 abaixo) |
| Resultado no VirusTotal | Link nas notas da Release (e Passo 2 abaixo) |
| Assinatura digital | **Não assinado.** Por isso o Windows (SmartScreen) mostra um aviso na primeira execução |

Alguns mecanismos do VirusTotal podem não responder a tempo e outros não analisam esse tipo de arquivo. O
resultado vale apenas para o arquivo com aquele SHA256 exato. Se o hash do seu arquivo for diferente, ele não é
o mesmo arquivo e você deve repetir a verificação.

## O que o programa faz (e não faz)

- É um player de vídeo local: abre arquivos do seu computador, toca com o VLC embutido e, se você
  pedir, grava a tela do player em `C:\Videos` usando o FFmpeg.
- O código Python do aplicativo **não contém chamadas de rede** (nenhum `urllib`, `requests` ou `socket`)
  e não tem telemetria. O único programa externo que ele inicia é o FFmpeg, para gravar.
  Confira você mesmo, na pasta do código-fonte:

  ```powershell
  Select-String -Path main.py, duplo\*.py -Pattern 'urllib|requests|socket|http'
  ```

  (A única ocorrência esperada é o endereço de esquema SVG em `duplo\icons.py`.)
- O botão de lixeira só envia para a Lixeira do Windows e pede confirmação; nunca apaga em definitivo.
- A instalação é por usuário e **não pede administrador**.

## Passo 1: conferir se o arquivo é o mesmo (SHA256)

No PowerShell, na pasta onde você baixou o instalador:

```powershell
Get-FileHash .\DuploPlayer-Setup-1.0.0.exe -Algorithm SHA256
```

O valor tem que ser igual ao das notas da Release. Se for diferente,
**não execute** o arquivo.

## Passo 2: conferir no VirusTotal

Duas formas, em <https://www.virustotal.com>:

- **Por hash (sem enviar o arquivo):** cole o SHA256 na busca. Se o arquivo já foi analisado, o relatório aparece.
- **Enviando o arquivo:** use a aba *File* e arraste o instalador.

Como ler: um ou dois alertas de mecanismos pouco conhecidos, com nomes genéricos como "Generic" ou "Heur",
são comuns em programas feitos com PyInstaller sem assinatura. Muitos alertas, ou alertas de antivírus grandes,
são motivo para não instalar e para abrir uma *issue* aqui.

## Passo 3: conferir a assinatura digital

```powershell
Get-AuthenticodeSignature .\DuploPlayer-Setup-1.0.0.exe | Format-List Status, SignerCertificate
```

O resultado esperado hoje é `NotSigned`. Significa que o instalador não tem assinatura de um certificado
de código (esses certificados são pagos e este é um projeto pessoal). A assinatura provaria quem publicou;
a ausência dela não indica, por si só, um vírus.

## Passo 4: escanear com o Microsoft Defender

```powershell
Start-MpScan -ScanType CustomScan -ScanPath "$env:USERPROFILE\Downloads\DuploPlayer-Setup-1.0.0.exe"
Get-MpThreatDetection | Select-Object -First 5
```

Se não houver detecção, `Get-MpThreatDetection` não mostra nada relacionado ao arquivo. Você também pode clicar
com o botão direito no instalador e escolher *Verificar com o Microsoft Defender*.

## Passo 5: instalar num ambiente isolado

Se quiser testar sem arriscar o seu computador:

- **Windows Sandbox** (Windows 10/11 Pro, Enterprise ou Education; ative em *Ativar ou desativar recursos do
  Windows*). Salve o arquivo abaixo como `duplo-teste.wsb` e dê duplo clique. A Sandbox abre sem rede e vê só a
  sua pasta de downloads, somente leitura. Troque `SEU_USUARIO` pelo seu usuário:

  ```xml
  <Configuration>
    <Networking>Disable</Networking>
    <MappedFolders>
      <MappedFolder>
        <HostFolder>C:\Users\SEU_USUARIO\Downloads</HostFolder>
        <ReadOnly>true</ReadOnly>
      </MappedFolder>
    </MappedFolders>
  </Configuration>
  ```

  Dentro da Sandbox, execute o instalador a partir da pasta mapeada. Tudo é apagado quando você fecha a janela.
- **Máquina virtual** (VirtualBox, VMware, Hyper-V) com um Windows 10/11 de teste e sem pastas compartilhadas.

## Passo 6: observar o que o programa faz enquanto roda

Com o Duplo Player aberto, veja se ele tem conexões de rede:

```powershell
Get-NetTCPConnection -OwningProcess (Get-Process DuploPlayer).Id -ErrorAction SilentlyContinue
```

Sem saída significa que ele não tem conexões TCP ativas. Para uma análise mais detalhada, use o
*Process Monitor* e o *TCPView* da Microsoft Sysinternals
(<https://learn.microsoft.com/sysinternals/>), filtrando pelo processo `DuploPlayer.exe`.

## Passo 7: gerar o aplicativo você mesmo (a prova mais forte)

Em vez de confiar no binário, compile do código-fonte e use o seu próprio resultado:

```powershell
git clone <url-do-repositorio>
cd duplo-player
.\setup.ps1      # Python 3.11 de 64 bits; baixa dependências e o VLC portátil (confere o SHA256 do VLC)
.\build.ps1      # gera dist\DuploPlayer\DuploPlayer.exe
```

Os detalhes estão no `README.md`. O hash do seu build **vai ser diferente** do publicado, porque builds
do PyInstaller não são reproduzíveis byte a byte. O que importa é que ele sai do código que você pode ler.
Os binários das Releases também podem ser gerados pelo workflow público `.github/workflows/build-windows.yml`,
cujo log mostra cada passo do build.

## Passo 8: ler o código

O código é pequeno (cerca de 2.500 linhas no pacote `duplo/`) e está descrito no `README.md`, na seção
*Arquitetura*. Os pontos que mais interessam a quem desconfia:

- `duplo/recording.py`: o único lugar que inicia um programa externo (FFmpeg).
- `duplo/recycle.py` e `duplo/explorer.py`: as únicas integrações com o Windows (lixeira e abrir pasta).
- `THIRD-PARTY.md`: lista de componentes de terceiros embutidos (VLC, FFmpeg, Qt, NumPy) e suas licenças.

## Se algo parecer errado

- Não execute o instalador e abra uma *issue* neste repositório com o resultado do Passo 1 e do Passo 2.
- Para remover uma instalação existente: *Configurações > Aplicativos > Aplicativos instalados > Duplo Player > Desinstalar*.
  As gravações em `C:\Videos` não são apagadas pelo desinstalador.
- Se o seu antivírus marcar o arquivo como suspeito, a maioria dos fabricantes aceita o envio do arquivo como falso
  positivo para reanálise.
