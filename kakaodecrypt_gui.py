#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
KakaoTalk Decrypt GUI
- guess_user_id.py 와 kakaodecrypt.py 를 Tkinter GUI로 통합한 스크립트입니다.
- 이 스크립트를 실행하기 위해서는 'pycryptodome' 라이브러리가 설치되어 있어야 합니다.
  (pip install pycryptodome)
"""

import sys
import sqlite3
import json
import hashlib
import base64
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from collections import Counter
import os
import shutil

#
# --- 원본 kakaodecrypt.py의 KakaoDecrypt 클래스 ---
#
try:
    from Crypto.Cipher import AES
except ImportError:
    print("오류: 'pycryptodome' 라이브러리를 찾을 수 없습니다.")
    print("터미널(CMD)에서 'pip install pycryptodome' 명령어를 실행해 설치해주세요.")
    sys.exit(1)

#
# *** 수정: 사용자님이 제공한 올바른 KakaoDecrypt 클래스로 교체 ***
#
class KakaoDecrypt:
  key_cache = {}

  # Reimplementation of com.kakao.talk.dream.Projector.incept() from libdream.so
  @staticmethod
  def incept(n):
    dict1 = ['adrp.ldrsh.ldnp', 'ldpsw', 'umax', 'stnp.rsubhn', 'sqdmlsl', 'uqrshl.csel', 'sqshlu', 'umin.usubl.umlsl', 'cbnz.adds', 'tbnz',
             'usubl2', 'stxr', 'sbfx', 'strh', 'stxrb.adcs', 'stxrh', 'ands.urhadd', 'subs', 'sbcs', 'fnmadd.ldxrb.saddl',
             'stur', 'ldrsb', 'strb', 'prfm', 'ubfiz', 'ldrsw.madd.msub.sturb.ldursb', 'ldrb', 'b.eq', 'ldur.sbfiz', 'extr',
             'fmadd', 'uqadd', 'sshr.uzp1.sttrb', 'umlsl2', 'rsubhn2.ldrh.uqsub', 'uqshl', 'uabd', 'ursra', 'usubw', 'uaddl2',
             'b.gt', 'b.lt', 'sqshl', 'bics', 'smin.ubfx', 'smlsl2', 'uabdl2', 'zip2.ssubw2', 'ccmp', 'sqdmlal',
             'b.al', 'smax.ldurh.uhsub', 'fcvtxn2', 'b.pl']
    dict2 = ['saddl', 'urhadd', 'ubfiz.sqdmlsl.tbnz.stnp', 'smin', 'strh', 'ccmp', 'usubl', 'umlsl', 'uzp1', 'sbfx',
             'b.eq', 'zip2.prfm.strb', 'msub', 'b.pl', 'csel', 'stxrh.ldxrb', 'uqrshl.ldrh', 'cbnz', 'ursra', 'sshr.ubfx.ldur.ldnp',
             'fcvtxn2', 'usubl2', 'uaddl2', 'b.al', 'ssubw2', 'umax', 'b.lt', 'adrp.sturb', 'extr', 'uqshl',
             'smax', 'uqsub.sqshlu', 'ands', 'madd', 'umin', 'b.gt', 'uabdl2', 'ldrsb.ldpsw.rsubhn', 'uqadd', 'sttrb',
             'stxr', 'adds', 'rsubhn2.umlsl2', 'sbcs.fmadd', 'usubw', 'sqshl', 'stur.ldrsh.smlsl2', 'ldrsw', 'fnmadd', 'stxrb.sbfiz',
             'adcs', 'bics.ldrb', 'l1ursb', 'subs.uhsub', 'ldurh', 'uabd', 'sqdmlal']
    word1 = dict1[  n      % len(dict1) ]
    word2 = dict2[ (n+31) % len(dict2) ]
    return word1 + '.' + word2

  @staticmethod
  def genSalt(user_id, encType):
    if user_id <= 0:
      return b'\0'*16

    prefixes = ['','','12','24','18','30','36','12','48','7','35','40','17','23','29',
                'isabel','kale','sulli','van','merry','kyle','james', 'maddux',
                'tony', 'hayden', 'paul', 'elijah', 'dorothy', 'sally', 'bran',
                KakaoDecrypt.incept(830819), 'veil']
    try:
      salt = prefixes[encType] + str(user_id)
      salt = salt[0:16]
    except IndexError:
      raise ValueError('Unsupported encoding type %i' % encType)
    salt = salt + '\0' * (16 - len(salt))
    return salt.encode('UTF-8')

  @staticmethod
  def pkcs16adjust(a, aOff, b):
      x = (b[len(b) - 1] & 0xff) + (a[aOff + len(b) - 1] & 0xff) + 1
      a[aOff + len(b) - 1] = x % 256
      x = x >> 8;
      for i in range(len(b)-2, -1, -1):
        x = x + (b[i] & 0xff) + (a[aOff + i] & 0xff)
        a[aOff + i] = x % 256
        x = x >> 8

  # PKCS12 key derivation as implemented in Bouncy Castle (using SHA1).
  # See org/bouncycastle/crypto/generators/PKCS12ParametersGenerator.java.
  @staticmethod
  def deriveKey(password, salt, iterations, dkeySize):
    password = (password + b'\0').decode('ascii').encode('utf-16-be')

    hasher = hashlib.sha1()
    v = hasher.block_size
    u = hasher.digest_size

    D = [ 1 ] * v
    S = [ 0 ] * v * int((len(salt) + v - 1) / v)
    for i in range(0, len(S)):
      S[i] = salt[i % len(salt)]
    P = [ 0 ] * v * int((len(password) + v - 1) / v)
    for i in range(0, len(P)):
      P[i] = password[i % len(password)]

    I = S + P

    B = [ 0 ] * v
    c = int((dkeySize + u - 1) / u)

    dKey = [0] * dkeySize
    for i in range(1, c+1):
      hasher = hashlib.sha1()
      hasher.update(bytes(D))
      hasher.update(bytes(I))
      A = hasher.digest()

      for j in range(1, iterations):
        hasher = hashlib.sha1()
        hasher.update(A)
        A = hasher.digest()

      A = list(A)
      for j in range(0, len(B)):
        B[j] = A[j % len(A)]

      for j in range(0, int(len(I)/v)):
        KakaoDecrypt.pkcs16adjust(I, j * v, B)

      start = (i - 1) * u
      if i == c:
        dKey[start : dkeySize] = A[0 : dkeySize-start]
      else:
        dKey[start : start+len(A)] = A[0 : len(A)]

    return bytes(dKey)

  @staticmethod
  def decrypt(user_id, encType, b64_ciphertext):
    key = b'\x16\x08\x09\x6f\x02\x17\x2b\x08\x21\x21\x0a\x10\x03\x03\x07\x06'
    iv = b'\x0f\x08\x01\x00\x19\x47\x25\xdc\x15\xf5\x17\xe0\xe1\x15\x0c\x35'

    salt = KakaoDecrypt.genSalt(user_id, encType)
    if salt in KakaoDecrypt.key_cache:
      key = KakaoDecrypt.key_cache[salt]
    else:
      key = KakaoDecrypt.deriveKey(key, salt, 2, 32)
      KakaoDecrypt.key_cache[salt] = key
    encoder = AES.new(key, AES.MODE_CBC, iv)

    ciphertext = base64.b64decode(b64_ciphertext)
    if len(ciphertext) == 0:
      return b64_ciphertext
    padded = encoder.decrypt(ciphertext)
    try:
      plaintext = padded[:-padded[-1]]
    except IndexError:
      raise ValueError('Unable to decrypt data', ciphertext)
    try:
      return plaintext.decode('UTF-8')
    except UnicodeDecodeError:
      return plaintext

  #
  # --- *** 수정: 사용자님이 제공한 "권장 패치" 코드로 교체 *** ---
  #
  @staticmethod
  def decrypt_table(cur, dec_cur, table, schema, user_id):
      dec_table = table + '_dec'
      print(f"테이블 '{table}' 복호화 시도 (-> '{dec_table}')...")

      # 1) 원본 테이블 존재 확인
      try:
          cur.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,))
          row = cur.fetchone()
          if not row or row[0] is None:
              print(f"  오류: 테이블 '{table}'이(가) DB에 없습니다. 건너뜁니다.")
              return
          create_sql = row[0]
      except sqlite3.Error as e:
          print(f"  오류: sqlite_master에서 테이블 정보를 읽을 수 없습니다: {e}")
          return

      # 2) dec_table 생성 (원본 CREATE 문을 사용하되 이름만 변경)
      try:
          new_create = create_sql.replace(table, dec_table, 1)
          # 기존 테이블 있으면 삭제 후 생성
          dec_cur.execute(f"DROP TABLE IF EXISTS {dec_table}") # 'cur' 대신 'dec_cur' 사용
          dec_cur.execute(new_create)
      except sqlite3.OperationalError as e:
          print(f"  오류: '{dec_table}' 테이블 생성 실패: {e}")
          return

      # 3) 원본 데이터 읽기
      try:
          cur.execute(f"SELECT * FROM {table}")
      except sqlite3.OperationalError as e:
          print(f"  오류: '{table}' 데이터를 읽을 수 없습니다: {e}")
          return

      col_names = [d[0] for d in cur.description]

      rows = cur.fetchall()
      if not rows:
          print(f"  '{table}' 테이블에 데이터가 없습니다.")
          return

      # 4) 각 행 복호화 및 삽입
      for row_index, row in enumerate(rows):
          row = list(row)

          # encType 추출:먼저 'enc' 컬럼을 시도, 없으면 'v' 컬럼 JSON 내부의 'enc' 키 사용
          enc_type = None
          if 'enc' in col_names:
              enc_idx = col_names.index('enc')
              enc_type = row[enc_idx]

          if enc_type is None and 'v' in col_names:
              v_idx = col_names.index('v')
              try:
                  v_val = row[v_idx]
                  if v_val:
                      parsed = json.loads(v_val)
                      enc_type = parsed.get('enc')
              except Exception:
                  enc_type = None
          
          # enc_type이 여전히 None이면 int로 변환 시도 (숫자일 경우 대비)
          try:
              if enc_type is not None:
                  enc_type = int(enc_type)
              else:
                  enc_type = -1 # 유효하지 않은 값
          except ValueError:
              enc_type = -1 # 유효하지 않은 값

          # profile_id / user_id 결정 (원본 논리 유지)
          current_row_user_id = user_id # 기본값
          
          if table != 'chat_logs':
              if user_id is None:
                  # try open_profile user
                  try:
                      # 'cur'가 아닌 'dec_cur' (동일 DB 커넥션) 사용
                      dec_cur.execute('SELECT user_id FROM open_profile LIMIT 1')
                      profile_id_row = dec_cur.fetchone()
                      if profile_id_row:
                          current_row_user_id = profile_id_row[0]
                      else:
                          print(f"  Skipping table '{table}' (to decrypt it, please specify user_id).")
                          return
                  except Exception:
                      print(f"  Skipping table '{table}' (to decrypt it, please specify user_id).")
                      return
              else:
                  current_row_user_id = user_id
          else:
              # chat_logs의 경우, 행의 user_id를 사용
              try:
                  current_row_user_id = row[col_names.index('user_id')]
              except (ValueError, IndexError):
                  print(f"  > [행 {row_index+1}] 'user_id' 컬럼을 찾을 수 없어 기본 user_id를 사용합니다.")
                  current_row_user_id = user_id # Fallback

          # 복호화 대상 컬럼 처리
          decrypted_row = list(row)
          for i, col in enumerate(col_names):
              if col in schema:
                  contents = row[i]
                  if contents is not None and enc_type >= 0:
                      try:
                          decrypted = KakaoDecrypt.decrypt(current_row_user_id, enc_type, contents)
                          
                          if isinstance(decrypted, bytes):
                              try:
                                  decrypted = decrypted.decode('utf-8')
                              except Exception:
                                  pass # 바이너리 BLOB으로 유지
                          decrypted_row[i] = decrypted
                      except Exception as e:
                          print(f"  > [행 {row_index+1}] '{col}' 복호화 오류: {e}")
                          decrypted_row[i] = contents
                  else:
                      decrypted_row[i] = contents # 복호화 조건 안맞으면 원본 유지

          # 삽입
          placeholders = ','.join(['?'] * len(decrypted_row))
          try:
              dec_cur.execute(f"INSERT INTO {dec_table} VALUES ({placeholders})", decrypted_row)
          except Exception as e:
              print(f"  오류: '{dec_table}'에 행 삽입 실패 (행 {row_index+1}): {e}")

      print(f"  성공: '{dec_table}' 테이블에 {len(rows)}개 행을 생성했습니다.")
#
# --- KakaoDecrypt 클래스 끝 ---
#


#
# --- 원본 guess_user_id.py의 KakaoDbGuessUserId 클래스 (수정됨) ---
#
class KakaoDbGuessUserId:
    @staticmethod
    def run(db_file):
        # 이 함수는 GUI 로깅을 위해 print()를 사용하고,
        # GUI에 최상위 ID를 전달하기 위해 top_guess_id를 반환합니다.
        try:
            con = sqlite3.connect(db_file)
            cur = con.cursor()
            cur.execute('SELECT id, members FROM chat_rooms')
            chat_members = { row[0]: [] if row[1] is None else json.loads(row[1]) for row in cur.fetchall()}
        except Exception as e:
            print(f"오류: chat_rooms 테이블 읽기 실패. '{db_file}' 파일이 아니거나 손상되었습니다.")
            print(f"상세: {e}")
            return None, 0

        found = []
        try:
            for chat_id in chat_members:
                if len(chat_members[chat_id]) > 0:
                    exclude = ','.join(list(map(str, chat_members[chat_id])))
                    cur.execute(f"SELECT DISTINCT user_id FROM chat_logs WHERE chat_id = {chat_id} AND user_id NOT IN ({exclude})")
                    for row in cur.fetchall():
                        found.append(row[0])
        except Exception as e:
            print(f"오류: chat_logs 테이블 읽기 실패.")
            print(f"상세: {e}")
            con.close()
            return None, 0

        con.close()
        total = len(found)
        top_guess_id = None

        if total > 0:
            print('가능한 User ID 목록 (확률순):')
            found_counter = Counter(found)
            
            # 확률순으로 정렬
            sorted_found = sorted(found_counter.items(), key=lambda item: item[1], reverse=True)
            top_guess_id = sorted_found[0][0] # 첫 번째 항목의 ID

            for user_id, count in sorted_found:
                prob = count * 100 / total
                print('  %20d (prob %5.2f%%)' % (user_id, prob))
        else:
            print('User ID를 찾을 수 없습니다.')

        return top_guess_id, total # 최상위 ID와 총 개수 반환

#
# --- GUI 애플리케이션 ---
#
class DecryptApp:
    def __init__(self, root):
        self.root = root
        self.root.title("카카오톡 복호화 도구")
        self.root.geometry("600x600")

        self.talk_db_var = tk.StringVar()
        self.friends_db_var = tk.StringVar()
        self.user_id_var = tk.StringVar()

        # --- 위젯 프레임 ---
        main_frame = ttk.Frame(root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- 1. KakaoTalk.db (대화) ---
        talk_frame = ttk.LabelFrame(main_frame, text=" 1. KakaoTalk.db (대화 DB) ", padding="10")
        talk_frame.pack(fill=tk.X, pady=5)
        
        talk_btn = ttk.Button(talk_frame, text="파일 선택", command=self.select_talk_db)
        talk_btn.pack(side=tk.LEFT, padx=5)
        
        talk_label = ttk.Label(talk_frame, textvariable=self.talk_db_var, foreground="gray")
        talk_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # --- 2. User ID 추측 ---
        guess_frame = ttk.LabelFrame(main_frame, text=" 2. User ID ", padding="10")
        guess_frame.pack(fill=tk.X, pady=5)
        
        self.guess_btn = ttk.Button(guess_frame, text="User ID 추측하기", command=self.run_guess_id, state=tk.DISABLED)
        self.guess_btn.pack(fill=tk.X)
        
        ttk.Label(guess_frame, text="사용할 User ID:").pack(side=tk.LEFT, padx=(0, 5), pady=5)
        self.user_id_entry = ttk.Entry(guess_frame, textvariable=self.user_id_var, width=20)
        self.user_id_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, pady=5)

        # --- 3. KakaoTalk2.db (친구) ---
        friends_frame = ttk.LabelFrame(main_frame, text=" 3. KakaoTalk2.db (친구 DB) ", padding="10")
        friends_frame.pack(fill=tk.X, pady=5)
        
        friends_btn = ttk.Button(friends_frame, text="파일 선택", command=self.select_friends_db)
        friends_btn.pack(side=tk.LEFT, padx=5)
        
        friends_label = ttk.Label(friends_frame, textvariable=self.friends_db_var, foreground="gray")
        friends_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # --- 4. 복호화 실행 ---
        self.decrypt_btn = ttk.Button(main_frame, text="DB 파일 복호화 실행", command=self.run_decrypt, state=tk.DISABLED)
        self.decrypt_btn.pack(fill=tk.X, pady=10)

        # --- 5. 로그 ---
        log_frame = ttk.LabelFrame(main_frame, text=" 로그 ", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=10, font=("Consolas", 9))
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # --- Stdout 리디렉션 ---
        self.redirector = TextRedirector(self.log_text)
        sys.stdout = self.redirector
        sys.stderr = self.redirector

        print("GUI 준비 완료. 복호화할 파일을 선택하세요.")
        print("---")

    def check_decrypt_button_state(self):
        # 모든 조건이 만족될 때만 복호화 버튼 활성화
        if self.talk_db_var.get() and self.friends_db_var.get() and self.user_id_var.get():
            self.decrypt_btn.config(state=tk.NORMAL)
        else:
            self.decrypt_btn.config(state=tk.DISABLED)

    def select_talk_db(self):
        path = filedialog.askopenfilename(title="KakaoTalk.db (대화) 파일을 선택하세요", filetypes=[("Database files", "*.db")])
        if path:
            self.talk_db_var.set(path)
            self.guess_btn.config(state=tk.NORMAL) # ID 추측 버튼 활성화
            print(f"대화 DB 선택됨: {path}")
            self.check_decrypt_button_state()

    def select_friends_db(self):
        path = filedialog.askopenfilename(title="KakaoTalk2.db (친구) 파일을 선택하세요", filetypes=[("Database files", "*.db")])
        if path:
            self.friends_db_var.set(path)
            print(f"친구 DB 선택됨: {path}")
            self.check_decrypt_button_state()

    def run_guess_id(self):
        # GUI가 멈추지 않도록 스레드에서 실행
        threading.Thread(target=self._guess_id_thread, daemon=True).start()

    def _guess_id_thread(self):
        self.guess_btn.config(state=tk.DISABLED)
        print("--- User ID 추측 시작 ---")
        db_file = self.talk_db_var.get()
        if not db_file:
            print("오류: KakaoTalk.db 파일이 선택되지 않았습니다.")
            self.guess_btn.config(state=tk.NORMAL)
            return

        try:
            top_id, total = KakaoDbGuessUserId.run(db_file)
            if top_id:
                print(f"가장 확률이 높은 User ID: {top_id} (을)를 자동으로 입력합니다.")
                # GUI 업데이트는 메인 스레드에서
                self.root.after(0, lambda: self.user_id_var.set(str(top_id)))
            
            print("--- User ID 추측 완료 ---")
        except Exception as e:
            print(f"User ID 추측 중 심각한 오류 발생: {e}")
        
        self.root.after(0, self.check_decrypt_button_state)
        self.guess_btn.config(state=tk.NORMAL)


    def run_decrypt(self):
        # GUI가 멈추지 않도록 스레드에서 실행
        threading.Thread(target=self._decrypt_thread, daemon=True).start()

    def _decrypt_thread(self):
        self.decrypt_btn.config(state=tk.DISABLED)
        print("--- 복호화 작업 시작 ---")
        
        try:
            user_id = int(self.user_id_var.get())
        except ValueError:
            print(f"오류: User ID '{self.user_id_var.get()}' (이)가 올바른 숫자가 아닙니다.")
            self.decrypt_btn.config(state=tk.NORMAL)
            return
            
        talk_db_path = self.talk_db_var.get()
        friends_db_path = self.friends_db_var.get()

        try:
            # --- 1. 백업 및 출력 경로 설정 ---
            # __file__은 스크립트가 pyinstaller로 패키징되었을 때를 고려하여 안전하게 사용
            if getattr(sys, 'frozen', False):
                script_dir = os.path.dirname(sys.executable)
            else:
                script_dir = os.path.dirname(os.path.abspath(__file__))
                
            backup_dir = os.path.join(script_dir, "DB Backup")
            os.makedirs(backup_dir, exist_ok=True)

            # 출력 파일 경로 (스크립트와 동일한 위치)
            output_talk_db = os.path.join(script_dir, "KakaoTalk_decrypted.db")
            output_friends_db = os.path.join(script_dir, "KakaoTalk2_decrypted.db")

            # 백업 파일 경로 (DB Backup 폴더 내부)
            backup_talk_path = os.path.join(backup_dir, os.path.basename(talk_db_path))
            backup_friends_path = os.path.join(backup_dir, os.path.basename(friends_db_path))

            # --- 2. 원본 파일 백업 ---
            print(f"원본 백업 중: {os.path.basename(talk_db_path)} -> {backup_dir}{os.sep}")
            shutil.copy2(talk_db_path, backup_talk_path)
            print(f"원본 백업 중: {os.path.basename(friends_db_path)} -> {backup_dir}{os.sep}")
            shutil.copy2(friends_db_path, backup_friends_path)

            # --- 3. 복호화할 대상 파일 복사 ---
            print(f"복호화 대상 사본 생성: {output_talk_db}")
            shutil.copy2(talk_db_path, output_talk_db)
            print(f"복호화 대상 사본 생성: {output_friends_db}")
            shutil.copy2(friends_db_path, output_friends_db)


            # --- 4. 복호화 실행 (사본 대상) ---
            # 1. KakaoTalk.db (대화) 복호화 스키마
            enc_schema_talk = {
                'chat_logs': ['message', 'attachment'],
                'chat_rooms': ['last_message'],
            }
            self._decrypt_db_logic(output_talk_db, user_id, enc_schema_talk) # output_talk_db
            print(f"'{os.path.basename(output_talk_db)}' 복호화 완료.")

            # 2. KakaoTalk2.db (친구) 복호화 스키마
            enc_schema_friends = {
                'friends':   ['uuid', 'phone_number', 'raw_phone_number', 'name',
                              'profile_image_url', 'full_profile_image_url',
                              'original_profile_image_url', 'status_message', 'v',
                              'board_v', 'ext', 'nick_name', 'contact_name'],
                'item': ['v'], 
                'item_resource': ['v'], 
            }
            self._decrypt_db_logic(output_friends_db, user_id, enc_schema_friends) # output_friends_db
            print(f"'{os.path.basename(output_friends_db)}' 복호화 완료.")
            
            print("--- 모든 복호화 작업 완료 ---")
            messagebox.showinfo("작업 완료", f"복호화 완료!\n스크립트 폴더에 {os.path.basename(output_talk_db)} 및 {os.path.basename(output_friends_db)} 파일이 생성되었습니다.")

        except Exception as e:
            print(f"복호화 중 심각한 오류 발생: {e}")
            messagebox.showerror("작업 오류", f"복호화 중 오류가 발생했습니다:\n{e}")
            
        self.decrypt_btn.config(state=tk.NORMAL)

    def _decrypt_db_logic(self, db_file, user_id, schema):
        # kakaodecrypt.py의 main 로직을 함수로 분리
        print(f"--- '{db_file}' 처리 중 ---")
        try:
            con = sqlite3.connect(db_file)
            cur = con.cursor()
            dec_cur = con.cursor()

            for table in schema:
                KakaoDecrypt.decrypt_table(cur, dec_cur, table, schema[table], user_id)
            
            con.commit()
            con.close()
        except sqlite3.OperationalError as e:
            print(f"  오류: '{db_file}' DB 작업 실패. 파일이 암호화되어 있거나, 권한이 없거나, 손상되었을 수 있습니다.")
            print(f"  상세: {e}")
        except Exception as e:
            print(f"  '{db_file}' 처리 중 예외 발생: {e}")
            if 'con' in locals():
                con.close()


# GUI의 ScrolledText 위젯으로 stdout/stderr를 리디렉션하는 클래스
class TextRedirector:
    def __init__(self, widget):
        self.widget = widget

    def write(self, s):
        def _write():
            self.widget.config(state=tk.NORMAL)
            self.widget.insert(tk.END, s)
            self.widget.see(tk.END)
            self.widget.config(state=tk.DISABLED)
        
        # Tkinter 위젯 업데이트는 항상 메인 스레드에서
        try:
            # GUI가 초기화되었다면 'after' 사용
            self.widget.after(0, _write)
        except:
            # GUI가 아직 준비되지 않았다면 (초기 오류) 그냥 print
            print(s, file=sys.__stdout__)


    def flush(self):
        pass # Tkinter Text 위젯은 flush가 필요 없음

# --- 애플리케이션 실행 ---
if __name__ == '__main__':
    # kakao_viewer.html과 충돌을 피하기 위해,
    # GUI 스크립트는 터미널에서 직접 실행해야 합니다.
    # (웹 브라우저에서는 실행되지 않습니다)
    try:
        root = tk.Tk()
        app = DecryptApp(root)
        root.mainloop()
    except Exception as e:
        print(f"GUI 실행 중 오류 발생: {e}")
        print("Tkinter GUI를 지원하는 환경에서 실행해야 합니다.")

