"""Interface text in English and Brazilian Portuguese.

Every user-facing string lives in one table, as a (Portuguese, English) pair, so the
two languages stay side by side and a test can check that none is missing. This module
has no Qt imports, which keeps `model.py` free of any interface dependency.

The language is chosen once at start-up (see `init`); a change made by the user
applies the next time the app is opened.
"""
import os

LANGUAGES = {'en': 'English', 'pt': 'Português (Brasil)'}
_current = 'en'

# key: (português, English). Placeholders use str.format fields and must match.
_T = {
    # --- enum labels (model) ---
    'repeat.off': ('Sem repetição', 'No repeat'),
    'repeat.one': ('Repetir vídeo', 'Repeat video'),
    'repeat.all': ('Repetir lista', 'Repeat list'),
    'order.sequential': ('Sequencial', 'Sequential'),
    'order.random_video': ('Aleatório vídeo', 'Random video'),
    'order.shuffle_list': ('Aleatório lista', 'Shuffle list'),

    # --- welcome screen and selection hint (view) ---
    'view.a': ('PERSPECTIVA A', 'VIEW A'),
    'view.b': ('PERSPECTIVA B', 'VIEW B'),
    'view.title': ('Um vídeo. Duas perspectivas.', 'One video. Two views.'),
    'view.welcome': ('Abra um vídeo ou arraste seus arquivos para cá.\n'
                     'Ctrl+S + arrastar: ampliar uma região • Ctrl+D: dividir a tela',
                     'Open a video or drag your files here.\n'
                     'Ctrl+S + drag: zoom into a region • Ctrl+D: split the screen'),
    'view.select_hint': ('Clique e arraste para selecionar o zoom', 'Click and drag to select the zoom area'),

    # --- keys named in tooltips ---
    'key.space': ('Espaço', 'Space'),

    # --- main window: sidebar, labels ---
    'list.count': ('LISTA · {n} vídeos', 'LIST · {n} videos'),
    'file.none': ('Nenhum vídeo aberto', 'No video open'),
    'label.speed': ('Velocidade', 'Speed'),
    'ab.off': ('A–B desativado', 'A–B off'),
    'ab.wait': ('A {a} · marque B', 'A {a} · set B'),
    'ab.range': ('A {a} → B {b}', 'A {a} → B {b}'),
    'zoom.full': ('quadro completo', 'full frame'),
    'zoom.factor': ('zoom {factor:.1f}×', 'zoom {factor:.1f}×'),
    'record.idle': ('Gravações: C:\\Videos • Ctrl+G inicia / encerra',
                    'Recordings: C:\\Videos • Ctrl+G starts / stops'),

    # --- main window: buttons (also used as tooltips and accessible names) ---
    'btn.open_files': ('Abrir vídeos', 'Open videos'),
    'btn.open_folder': ('Abrir pasta', 'Open folder'),
    'btn.previous': ('Vídeo anterior', 'Previous video'),
    'btn.play_pause': ('Pausar / continuar', 'Pause / resume'),
    'btn.next': ('Próximo vídeo', 'Next video'),
    'btn.stop': ('Parar', 'Stop'),
    'btn.frame': ('Avançar quadro', 'Step one frame'),
    'btn.order': ('Ordem: {mode}', 'Order: {mode}'),
    'btn.record': ('Iniciar / encerrar gravação em C:\\Videos', 'Start / stop recording to C:\\Videos'),
    'btn.join': ('Juntar os trechos gravados em um só vídeo', 'Join the recorded segments into one video'),
    'btn.noise': ('Ligar / desligar supressão de ruído', 'Turn noise suppression on / off'),
    'btn.mute': ('Silenciar', 'Mute'),
    'btn.split': ('Dividir / unir tela', 'Split / merge screen'),
    'btn.zoom': ('Zoom por seleção', 'Selection zoom'),
    'btn.reset_zoom': ('Restaurar zoom da tela selecionada', 'Reset zoom of the selected view'),
    'btn.rotate': ('Girar tela selecionada 90° no sentido horário', 'Rotate the selected view 90° clockwise'),
    'btn.mark_a': ('Marcar A', 'Set A'),
    'btn.mark_b': ('Marcar B', 'Set B'),
    'btn.clear_ab': ('Limpar A–B', 'Clear A–B'),
    'btn.fullscreen': ('Tela cheia', 'Full screen'),
    'btn.reveal': ('Abrir pasta do vídeo', 'Show video in folder'),
    'btn.trash': ('Enviar vídeo à lixeira', 'Move video to the Recycle Bin'),
    'btn.sidebar': ('Mostrar / ocultar lista', 'Show / hide list'),
    'btn.remove': ('Remover seleção da lista, mantendo o arquivo', 'Remove the selection from the list (keeps the file)'),
    'btn.help': ('Atalhos', 'Shortcuts'),
    'btn.repeat_tip': ('{mode}. Clique para mudar a repetição.', '{mode}. Click to change the repeat mode.'),
    'btn.order_tip': ('Ordem: {mode}. Clique para mudar o modo.', 'Order: {mode}. Click to change the mode.'),
    'speed.tip': ('-: câmera lenta até 0,25×; +: aumentar velocidade até 2×; [ / ]: ajustar velocidade',
                  '-: slow motion down to 0.25×; +: speed up to 2×; [ / ]: adjust speed'),
    'noise.accessible': ('Intensidade da supressão de ruído, de 0 a 100%', 'Noise suppression strength, 0 to 100%'),
    'noise.strength_tip': ('Intensidade da supressão: {percent}% (0% = áudio original)',
                           'Suppression strength: {percent}% (0% = original audio)'),
    'noise.off': ('desligada', 'off'),
    'noise.tip': ('Supressão de ruído: {state} (Ctrl+H)', 'Noise suppression: {state} (Ctrl+H)'),

    # --- status bar ---
    'status.start': ('Abra um vídeo para começar. Passe o mouse nos ícones para ver suas funções.',
                     'Open a video to start. Hover over the icons to see what they do.'),
    'status.added': ('{n} vídeo(s) adicionado(s) à lista.', '{n} video(s) added to the list.'),
    'status.none_new': ('Nenhum vídeo novo encontrado. Confira os formatos ou a lista.',
                        'No new videos found. Check the formats or the list.'),
    'status.loading': ('Carregando vídeo…', 'Loading video…'),
    'status.stopped': ('Reprodução parada. Espaço para reiniciar.', 'Playback stopped. Press Space to restart.'),
    'status.end_of_list': ('Fim da lista. Ative Repetir lista para reiniciar.',
                           'End of list. Turn on Repeat list to start over.'),
    'status.order': ('Ordem: {mode} · repetição: {repeat}', 'Order: {mode} · repeat: {repeat}'),
    'status.repeat': ('Repetição: {mode}', 'Repeat: {mode}'),
    'status.finishing_recording': ('Finalizando a gravação…', 'Finishing the recording…'),
    'status.ab_needs_seek': ('Abra um vídeo que permita busca para marcar A–B.', 'Open a seekable video to set A–B.'),
    'status.ab_order': ('Marque A primeiro. B precisa estar pelo menos 0,1 s depois de A.',
                        'Set A first. B must be at least 0.1 s after A.'),
    'status.rate_refused': ('O motor não aceitou esta velocidade para o vídeo atual.',
                            'The player engine did not accept this speed for the current video.'),
    'status.zoom_on': ('Clique e arraste na perspectiva desejada. Ctrl+Z restaura o zoom da tela selecionada.',
                       "Click and drag on the view you want. Ctrl+Z resets the selected view's zoom."),
    'status.zoom_off': ('Zoom por seleção desativado.', 'Selection zoom is off.'),
    'status.shared': ('As perspectivas compartilham o mesmo quadro e o mesmo áudio.',
                      'The views share the same frame and the same audio.'),
    'status.revealed': ('Pasta aberta com o vídeo selecionado: {folder}', 'Folder opened with the video selected: {folder}'),
    'status.trashed': ('“{name}” enviado para a lixeira.', '“{name}” moved to the Recycle Bin.'),
    'status.playing': ('Reproduzindo · clique direito para acessar a pasta ou enviar à lixeira.',
                       'Playing · right-click to open the folder or move the video to the Recycle Bin.'),
    'status.paused': ('Pausado · E avança um quadro; Z ativa a seleção de zoom.',
                      'Paused · E steps one frame; Z turns on selection zoom.'),
    'status.play_failed': ('Falha ao reproduzir. O arquivo pode estar danificado ou ter um codec incompatível.',
                           'Playback failed. The file may be damaged or use an unsupported codec.'),

    # --- recording ---
    'rec.stop_tip': ('Encerrar gravação (Ctrl+G)', 'Stop recording (Ctrl+G)'),
    'rec.start_tip': ('Gravar exibição em C:\\Videos (Ctrl+G)', 'Record the display to C:\\Videos (Ctrl+G)'),
    'rec.active': ('● GRAVANDO trecho {n} • Ctrl+G encerra • {path}', '● RECORDING segment {n} • Ctrl+G stops • {path}'),
    'rec.segments': ('{n} trecho(s) gravado(s) • Ctrl+G grava outro • Ctrl+Shift+G junta em um só vídeo • {path}',
                     '{n} segment(s) recorded • Ctrl+G records another • Ctrl+Shift+G joins them into one video • {path}'),
    'rec.join_need': ('Grave pelo menos dois trechos com Ctrl+G antes de juntar.',
                      'Record at least two segments with Ctrl+G before joining.'),
    'rec.joining': ('Juntando {n} trechos em um só vídeo…', 'Joining {n} segments into one video…'),
    'rec.joined': ('Vídeo único salvo ({n} trechos): {path}', 'Single video saved ({n} segments): {path}'),
    'rec.join_not_deleted': ('trechos não excluídos: {names}', 'segments not deleted: {names}'),
    'rec.join_incomplete': ('O vídeo unido ficou mais curto que a soma dos trechos e foi descartado.',
                            'The joined video came out shorter than the segments together and was discarded.'),
    'rec.join_failed_title': ('Não foi possível juntar os trechos', 'Could not join the segments'),
    'rec.join_kept': ('Os trechos foram mantidos.\n\n{error}', 'The segments were kept.\n\n{error}'),
    'rec.join_missing': ('Trechos não encontrados:\n{paths}', 'Segments not found:\n{paths}'),
    'rec.finishing': ('Finalizando gravação…', 'Finishing the recording…'),
    'rec.saved': ('Gravação salva: {path}', 'Recording saved: {path}'),
    'rec.failed_info': ('Falha na gravação: {message}', 'Recording failed: {message}'),
    'rec.failed_title': ('Falha na gravação', 'Recording failed'),
    'rec.cannot_title': ('Não foi possível gravar', 'Could not record'),
    'rec.no_frame': ('Abra um vídeo e aguarde a primeira imagem antes de gravar.',
                     'Open a video and wait for the first image before recording.'),
    'rec.fell_behind': ('A gravação não acompanhou a reprodução. O trecho já gravado será finalizado.',
                        'The recording could not keep up with playback. The part already recorded will be finished.'),
    'rec.encoder_failed': ('O codificador de vídeo falhou.', 'The video encoder failed.'),
    'rec.temp_kept': ('{error}\nTemporários preservados em {work}', '{error}\nTemporary files kept in {work}'),

    # --- dialogs ---
    'dlg.open_videos': ('Abrir vídeos', 'Open videos'),
    'dlg.videos_filter': ('Vídeos ({patterns})', 'Videos ({patterns})'),
    'dlg.open_folder': ('Abrir pasta de vídeos', 'Open video folder'),
    'dlg.unavailable_title': ('Arquivo indisponível', 'File unavailable'),
    'dlg.unavailable_body': ('O arquivo não foi encontrado:\n{path}', 'The file was not found:\n{path}'),
    'dlg.cannot_open_folder': ('Não foi possível abrir a pasta', 'Could not open the folder'),
    'dlg.play_failed_title': ('Falha de reprodução', 'Playback failure'),
    'dlg.play_failed_body': ('Não foi possível reproduzir este vídeo.\nConfira se o arquivo está acessível e íntegro.',
                             'This video could not be played.\nCheck that the file is accessible and not corrupted.'),
    'trash.title': ('Enviar vídeo para a lixeira?', 'Move the video to the Recycle Bin?'),
    'trash.text': ('Enviar “{name}” para a lixeira do Windows?', 'Move “{name}” to the Windows Recycle Bin?'),
    'trash.info': ('{path}\n\nO vídeo será removido da lista. Você poderá recuperá-lo na lixeira.',
                   '{path}\n\nThe video will be removed from the list. You can restore it from the Recycle Bin.'),
    'trash.confirm': ('Enviar para a lixeira', 'Move to the Recycle Bin'),
    'trash.cancel': ('Cancelar', 'Cancel'),
    'trash.failed_title': ('Não foi possível enviar à lixeira', 'Could not move to the Recycle Bin'),
    'trash.failed_body': ('O arquivo foi mantido.\n\n{error}', 'The file was kept.\n\n{error}'),

    # --- context menu ---
    'menu.play_pause': ('Pausar / continuar', 'Pause / resume'),
    'menu.reveal': ('Abrir pasta do vídeo', 'Show video in folder'),
    'menu.trash': ('Enviar vídeo para a lixeira…', 'Move video to the Recycle Bin…'),
    'menu.zoom': ('Zoom por seleção (Ctrl+S / Z)', 'Selection zoom (Ctrl+S / Z)'),
    'menu.noise': ('Supressão de ruído: ligar / desligar (Ctrl+H)', 'Noise suppression: on / off (Ctrl+H)'),
    'menu.noise_strength': ('Intensidade da supressão de ruído', 'Noise suppression strength'),
    'menu.reset_zoom': ('Restaurar zoom desta perspectiva (Ctrl+Z / R)', "Reset this view's zoom (Ctrl+Z / R)"),
    'menu.rotate': ('Girar esta perspectiva 90° no sentido horário (Ctrl+R)', 'Rotate this view 90° clockwise (Ctrl+R)'),
    'menu.split': ('Dividir tela (Ctrl+D / D)', 'Split screen (Ctrl+D / D)'),
    'menu.speed': ('Velocidade / câmera lenta', 'Speed / slow motion'),
    'menu.fullscreen': ('Tela cheia (F11)', 'Full screen (F11)'),
    'menu.rec_stop': ('Encerrar gravação (Ctrl+G)', 'Stop recording (Ctrl+G)'),
    'menu.rec_start': ('Gravar exibição (Ctrl+G)', 'Record display (Ctrl+G)'),
    'menu.rec_join': ('Juntar {n} trecho(s) gravado(s) em um só vídeo (Ctrl+Shift+G)',
                      'Join {n} recorded segment(s) into one video (Ctrl+Shift+G)'),
    'menu.language': ('Idioma / Language', 'Idioma / Language'),
    'language.changed_title': ('Idioma alterado', 'Language changed'),
    'language.changed_body': ('O novo idioma será aplicado na próxima vez que você abrir o Duplo Player.',
                              'The new language will apply the next time you open Duplo Player.'),

    # --- shortcuts help ---
    'help.title': ('Atalhos do Duplo Player', 'Duplo Player shortcuts'),
    'help.body': (
        'Ctrl+O   Abrir vídeos\nCtrl+Shift+O   Abrir pasta\nEspaço   Pausar / continuar\n'
        'Ctrl+S / Z   Ativar/desativar zoom; clique e arraste na imagem\nCtrl+Z / R   Restaurar zoom da tela ativa\n'
        'Shift+R   Restaurar zoom das duas telas\nCtrl+R   Girar tela ativa 90° no sentido horário\n'
        'Ctrl+D / D   Dividir / unir tela\n'
        '3   Primeiro toque: A; segundo toque: B; próximo toque: novo trecho\nA / B   Marcar início / fim separadamente\nC   Limpar A–B\n'
        '-   Câmera lenta: 0,75× → 0,5× → 0,25× (limite do atalho)\n'
        '+   Aumentar velocidade, passar por 1× e acelerar até 2×\n'
        '[ / ]   Diminuir / aumentar velocidade\nE   Avançar um quadro\n'
        '← / →   Retroceder / avançar 5 segundos\n1 / 2   Vídeo anterior / próximo vídeo\nN / P   Próximo / anterior\n'
        'S   Parar\nM   Silenciar\nCtrl+H   Ligar/desligar supressão de ruído\nF11   Tela cheia: somente vídeo\nEsc   Sair da tela cheia / seleção de zoom\n'
        'Ctrl+L   Mostrar / ocultar lista\nCtrl+G   Iniciar / encerrar gravação (um trecho) em C:\\Videos\n'
        'Ctrl+Shift+G   Juntar os trechos gravados em um só vídeo\n\n'
        'Em tela cheia, leve o mouse à parte de baixo para ver a barra de tempo.\n'
        'Ctrl+S e arraste para ampliar, inclusive em tela cheia.\nClique em uma perspectiva para selecioná-la. O zoom é independente.\n'
        'As duas perspectivas reproduzem o MESMO vídeo, com um único áudio.\n'
        'Clique direito na imagem para abrir a pasta ou enviar o vídeo à lixeira.\n'
        'Abrir pasta adiciona os vídeos diretamente nessa pasta, sem subpastas.',
        'Ctrl+O   Open videos\nCtrl+Shift+O   Open folder\nSpace   Pause / resume\n'
        "Ctrl+S / Z   Turn zoom on/off; click and drag on the image\nCtrl+Z / R   Reset the active view's zoom\n"
        'Shift+R   Reset the zoom of both views\nCtrl+R   Rotate the active view 90° clockwise\n'
        'Ctrl+D / D   Split / merge screen\n'
        '3   First press: A; second press: B; next press: new range\nA / B   Set start / end separately\nC   Clear A–B\n'
        '-   Slow motion: 0.75× → 0.5× → 0.25× (the shortcut stops there)\n'
        '+   Speed up, passing through 1× and up to 2×\n'
        '[ / ]   Decrease / increase speed\nE   Step one frame\n'
        '← / →   Rewind / forward 5 seconds\n1 / 2   Previous / next video\nN / P   Next / previous\n'
        'S   Stop\nM   Mute\nCtrl+H   Turn noise suppression on/off\nF11   Full screen: video only\nEsc   Leave full screen / zoom selection\n'
        'Ctrl+L   Show / hide the list\nCtrl+G   Start / stop recording (one segment) to C:\\Videos\n'
        'Ctrl+Shift+G   Join the recorded segments into one video\n\n'
        'In full screen, move the mouse to the bottom to see the timeline.\n'
        'Ctrl+S and drag to zoom in, also in full screen.\nClick a view to select it. Zoom is independent for each view.\n'
        'Both views play the SAME video, with a single audio track.\n'
        'Right-click the image to open the folder or move the video to the Recycle Bin.\n'
        'Open folder adds the videos directly inside that folder, without subfolders.'),

    # --- audio, engine, Windows integration, start-up errors ---
    'audio.unavailable': ('Saída de áudio indisponível para PCM estéreo 48 kHz.',
                          'Audio output unavailable for 48 kHz stereo PCM.'),
    'engine.init_failed': ('Não foi possível inicializar o motor VLC.', 'Could not initialize the VLC engine.'),
    'explorer.windows_only': ('A abertura da pasta usa o Explorer do Windows.',
                              'Opening the folder uses Windows Explorer.'),
    'explorer.missing': ('O vídeo não foi encontrado no local original:\n{path}\n\n'
                         'Ele pode ter sido movido, renomeado ou removido.',
                         'The video was not found at its original location:\n{path}\n\n'
                         'It may have been moved, renamed or removed.'),
    'explorer.init_failed': ('O Windows não conseguiu iniciar o acesso à pasta (0x{code:08X}).',
                             'Windows could not start access to the folder (0x{code:08X}).'),
    'explorer.open_failed': ('O Windows não conseguiu abrir a pasta e selecionar o vídeo.\n{detail}',
                             'Windows could not open the folder and select the video.\n{detail}'),
    'recycle.windows_only': ('Esta versão usa a lixeira do Windows.', 'This version uses the Windows Recycle Bin.'),
    'recycle.bad_target': ('O destino precisa ser um arquivo de vídeo local existente.',
                           'The target must be an existing local video file.'),
    'recycle.fixed_only': ('A lixeira é permitida apenas em discos locais fixos. O arquivo foi mantido.',
                           'The Recycle Bin is only allowed on fixed local drives. The file was kept.'),
    'recycle.unavailable': ('O Windows não disponibilizou a lixeira para este arquivo.',
                            'Windows did not offer the Recycle Bin for this file.'),
    'recycle.cancelled': ('O Windows cancelou o envio à lixeira.', 'Windows cancelled the move to the Recycle Bin.'),
    'recycle.unconfirmed': ('O Windows não confirmou o envio à lixeira.',
                            'Windows did not confirm the move to the Recycle Bin.'),
    'start.failed_title': ('Duplo Player — falha ao iniciar', 'Duplo Player — failed to start'),
    'start.failed_body': ('Não foi possível iniciar o player.\n\n{error}\n\n'
                          'Use a pasta completa do aplicativo, incluindo o motor VLC.',
                          'The player could not start.\n\n{error}\n\n'
                          'Use the complete application folder, including the VLC engine.'),
    'start.error_title': ('Duplo Player — erro', 'Duplo Player — error'),
    'start.error_body': ('{error}\n\nDiagnóstico: {log}', '{error}\n\nDiagnostics: {log}'),
}


def system_language():
    """'pt' if the Windows (or POSIX) user locale is Portuguese, otherwise 'en'."""
    name = ''
    try:
        import ctypes
        buffer = ctypes.create_unicode_buffer(85)
        if ctypes.windll.kernel32.GetUserDefaultLocaleName(buffer, 85):
            name = buffer.value
    except Exception:
        pass
    if not name:
        try:
            import locale
            name = locale.getlocale()[0] or ''
        except Exception:
            name = ''
    return 'pt' if name.lower().startswith('pt') else 'en'


def set_language(code):
    global _current
    if code not in LANGUAGES:
        raise ValueError(f'Unsupported language: {code!r}')
    _current = code


def language():
    return _current


def init(settings=None):
    """Pick the language: DUPLO_LANG, then the saved setting, then the system locale."""
    choice = os.environ.get('DUPLO_LANG', '').strip().lower()
    if choice not in LANGUAGES and settings is not None:
        choice = str(settings.value('language', '')).strip().lower()
    if choice not in LANGUAGES:
        choice = system_language()
    set_language(choice)
    return choice


def tr(key, **fields):
    pair = _T.get(key)
    if pair is None:
        raise KeyError(f'Missing translation key: {key}')
    text = pair[0] if _current == 'pt' else pair[1]
    return text.format(**fields) if fields else text


def keys():
    return list(_T)


def pair(key):
    return _T[key]
