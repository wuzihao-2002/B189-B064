create_tbl_file_detail_sql = """
                                DROP TABLE IF EXISTS FileDetail;
                                CREATE TABLE FileDetail (
                                    line_num          INTEGER PRIMARY KEY,
                                    file_id           TEXT,
                                    file              TEXT,
                                    type              CHAR (1),
                                    last_update_date  TEXT,
                                    last_update_time  TEXT,
                                    last_updater      TEXT,
                                    uri               TEXT,
                                    parent_folder     TEXT,
                                    parent_uri        TEXT ,
                                    writers_can_share TEXT,
                                    domain            TEXT,
                                    owner             TEXT,
                                    writer            TEXT,
                                    reader            TEXT,
                                    check_result      CHAR (1),
                                    setting_result    CHAR (1),
                                    err_info          TEXT
                                );
                                CREATE INDEX FileDetail_file_id ON FileDetail (
                                    file_id
                                );
                            """
create_tbl_file_access_setting_info_sql = """
                                             DROP TABLE IF EXISTS FileAccessSettingInfo;
                                             CREATE TABLE FileAccessSettingInfo (
                                                 line_num       INTEGER PRIMARY KEY,
                                                 file_id        TEXT,
                                                 add_upd_writer TEXT,
                                                 add_upd_reader TEXT,
                                                 remover        TEXT
                                             );
                                          """
create_tbl_file_transfer_setting_info_sql = """
                                               DROP TABLE IF EXISTS FileTransferSettingInfo;
                                               CREATE TABLE FileTransferSettingInfo (
                                                   line_num       INTEGER PRIMARY KEY,
                                                   file_id        TEXT,
                                                   transfer_owner TEXT
                                               ); 
                                            """
create_tbl_file_moving_info_sql = """
                                     DROP TABLE IF EXISTS FileMovingInfo;
                                     CREATE TABLE FileMovingInfo (
                                         line_num  INTEGER PRIMARY KEY,
                                         file_id   TEXT,
                                         parent_id TEXT
                                     );
                                  """
create_tbl_file_actual_permission_info_sql = """
                                                DROP TABLE IF EXISTS FileActualPermissionInfo;
                                                CREATE TABLE FileActualPermissionInfo (
                                                    file_id           TEXT    PRIMARY KEY,
                                                    mime_type         TEXT,
                                                    trashed           TEXT,
                                                    writers_can_share TEXT,
                                                    actual_owner      TEXT,
                                                    actual_writer     TEXT,
                                                    actual_reader     TEXT,
                                                    owned_by_me       TEXT,
                                                    permission_info   TEXT
                                                );
                                             """

drop_tbl_file_detail_sql = """
                              DROP TABLE IF EXISTS FileDetail;
                           """
drop_tbl_file_access_setting_info_sql = """
                                           DROP TABLE IF EXISTS FileAccessSettingInfo;
                                        """
drop_tbl_file_transfer_setting_info_sql = """
                                             DROP TABLE IF EXISTS FileTransferSettingInfo;
                                          """
drop_tbl_file_moving_info_sql = """
                                   DROP TABLE IF EXISTS FileMovingInfo;
                                """

insert_file_detail_sql = """
                            INSERT INTO FileDetail (
                                  line_num,
                                  file_id,
                                  file,
                                  type,
                                  last_update_date,
                                  last_update_time,
                                  last_updater,
                                  uri,
                                  parent_folder,
                                  parent_uri,
                                  writers_can_share,
                                  domain,
                                  owner,
                                  writer,
                                  reader,
                                  check_result,
                                  setting_result,
                                  err_info
                              )
                              VALUES (
                                  ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?
                              );
                         """
insert_file_access_setting_info_sql = """
                                         INSERT INTO FileAccessSettingInfo (
                                               line_num,
                                               file_id,
                                               add_upd_writer,
                                               add_upd_reader,
                                               remover
                                           )
                                           VALUES (
                                               ?,?,?,?,?
                                           );
                                      """
insert_file_transfer_setting_info_sql = """
                                           INSERT INTO FileTransferSettingInfo (
                                                line_num,
                                                file_id,
                                                transfer_owner
                                             )
                                             VALUES (
                                                 ?,?,?
                                             );
                                        """
insert_file_moving_info_sql = """
                                 INSERT INTO FileMovingInfo (
                                       line_num,
                                       file_id,
                                       parent_id
                                   )
                                   VALUES (
                                       ?,?,?
                                   );
                              """
insert_file_actual_permission_info_sql = """
                                            INSERT INTO FileActualPermissionInfo (
                                                 file_id,
                                                 mime_type,
                                                 trashed,
                                                 writers_can_share,
                                                 actual_owner,
                                                 actual_writer,
                                                 actual_reader,
                                                 owned_by_me,
                                                 permission_info
                                             )
                                             VALUES (
                                                 ?,?,?,?,?,?,?,?,?
                                             );
                                         """

update_file_detail_check_result_sql = """
                                         UPDATE
                                             FileDetail
                                           SET
                                             check_result = ?
                                           WHERE
                                             line_num = ?; 
                                      """
update_file_detail_set_result_sql = """
                                       UPDATE
                                           FileDetail
                                         SET
                                           setting_result = ?,
                                           err_info = ?
                                         WHERE
                                           line_num = ?;
                                    """
update_file_detail_set_result_and_writer_sql = """
                                                  UPDATE
                                                      FileDetail
                                                    SET
                                                      setting_result = ?,
                                                      err_info = ?,
                                                      writer = ?
                                                    WHERE
                                                      line_num = ?;
                                               """

select_file_detail_sql = """
                            SELECT 
                                file, type, last_update_date, last_update_time, last_updater, uri, parent_folder,
                                parent_uri, writers_can_share, domain, owner, writer, reader, check_result,
                                setting_result, err_info
                              FROM
                                FileDetail
                              ORDER BY line_num;
                         """
select_access_setting_info_sql = """
                                    SELECT
                                        access.line_num, access.file_id, access.add_upd_writer, access.add_upd_reader, 
                                        access.remover, detail.file
                                      FROM
                                          FileAccessSettingInfo as access
                                        INNER JOIN
                                          FileDetail as detail
                                        ON 
                                          access.line_num = detail.line_num;
                                 """
select_transfer_setting_and_file_detail_info_sql = """
                                                      SELECT
                                                          trans.line_num, trans.file_id, trans.transfer_owner,
                                                          detail.file, detail.writer, detail.reader, detail.err_info
                                                        FROM
                                                            FileTransferSettingInfo as trans
                                                          INNER JOIN
                                                            FileDetail as detail
                                                          ON 
                                                            trans.line_num = detail.line_num;
                                                   """
select_file_moving_and_file_detail_info_sql = """
                                                 SELECT
                                                     mov.line_num, mov.file_id, mov.parent_id,
                                                     detail.file, detail.owner, detail.writer, detail.reader
                                                   FROM
                                                       FileMovingInfo as mov
                                                     INNER JOIN
                                                       FileDetail as detail
                                                     ON
                                                       mov.line_num = detail.line_num;
                                              """
select_row_count_sql = """
                          SELECT COUNT(line_num) FROM ?;
                       """
select_file_actual_permission_by_file_id_sql = """
                                                  SELECT 
                                                      file_id, mime_type, trashed, writers_can_share,
                                                      actual_owner, actual_writer, actual_reader,
                                                      owned_by_me, permission_info
                                                    FROM
                                                      FileActualPermissionInfo
                                                    WHERE
                                                      file_id = ?;
                                               """

access_setting_tbl = "FileAccessSettingInfo"
transfer_setting_tbl = "FileTransferSettingInfo"
file_moving_tbl = "FileMovingInfo"

vacuum_sql = "VACUUM;"
