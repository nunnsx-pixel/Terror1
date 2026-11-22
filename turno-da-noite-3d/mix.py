import sys, subprocess
sys.path.insert(0, '../turno-da-noite')
import render
render.LINES = []
render.build_audio('bed.wav')
V = [(1.0,'01_prot_intro'),(6.5,'02_col_falta'),(13.9,'03_prot_luzes'),(19.0,'04_prot_rua'),(23.9,'05_col_vendo'),
     (26.2,'06_prot_gerente'),(31.3,'07_ger_fundos'),(41.0,'08_prot_alarme'),(46.8,'09_prot_celular'),
     (51.7,'10_col_dentro'),(54.0,'11_ger_ignora'),(59.0,'12_prot_agora')]
cmd = ['ffmpeg','-y','-loglevel','error','-i','bed.wav']
for _, n in V: cmd += ['-i', f'voz/{n}.mp3']
fc = '[0:a]volume=0.55[b];'
for i,(t,_) in enumerate(V,1):
    ms = int(t*1000)
    fc += f'[{i}:a]volume=1.6,adelay={ms}|{ms}[v{i}];'
fc += '[b]' + ''.join(f'[v{i}]' for i in range(1,len(V)+1)) + f'amix=inputs={len(V)+1}:normalize=0:dropout_transition=0,alimiter=limit=0.95,atrim=0:70[a]'
cmd += ['-filter_complex', fc, '-map', '[a]', '-ar', '44100', 'audio.wav']
subprocess.run(cmd, check=True)
