CREATE OR REPLACE PACKAGE accounting AS
  g_total NUMBER := 0;
  FUNCTION adjusted(p_amount NUMBER) RETURN NUMBER;
  PROCEDURE calculate(p_count NUMBER);
END accounting;
/
CREATE OR REPLACE PACKAGE BODY accounting AS
  g_total NUMBER := 0;

  FUNCTION adjusted(p_amount NUMBER) RETURN NUMBER IS
  BEGIN
    RETURN p_amount * 1.1;
  END adjusted;

  PROCEDURE calculate(p_count NUMBER) IS
    v_amount NUMBER := 0;
  BEGIN
    g_total := 0;
    FOR i IN 1..p_count LOOP
      v_amount := adjusted(i);
      IF v_amount > 10 THEN
        g_total := g_total + v_amount;
      ELSE
        g_total := 0;
      END IF;
    END LOOP;
    INSERT INTO totals(amount) VALUES (g_total);
    COMMIT;
  EXCEPTION
    WHEN OTHERS THEN
      ROLLBACK;
      RAISE;
  END calculate;
BEGIN
  g_total := 0;
END accounting;
/
