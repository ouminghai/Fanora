import { BadgeCheck, Coins, RadioTower, Sparkles, Users, WalletCards } from "lucide-react";
import { fanJourney } from "@/data/fanora";
import styles from "./Process.module.css";

const journeyIcons = [WalletCards, Users, Coins, BadgeCheck];

export default function Process() {
  return (
    <section id="fan-journey" className={styles.networkSection}>
      <div className={styles.universe} aria-hidden="true">
        <div className={styles.stars} />
        <div className={styles.nebulaOne} />
        <div className={styles.nebulaTwo} />
      </div>
      <div className={`${styles.networkContainer} container`}>
        <header className={styles.networkHeader}>
          <span><RadioTower /> BLOCKCHAIN NETWORK</span>
          <h2>从加入社区到拥有链上粉丝身份</h2>
          <p>每一次真实参与，都会沿着 Monad 链路沉淀为可验证的身份资产。</p>
        </header>

        <div className={styles.chainMap}>
          {fanJourney.map((step, index) => {
            const Icon = journeyIcons[index] ?? Sparkles;
            return (
              <div className={styles.chainSegment} key={step.id}>
                <article className={styles.chainNode}>
                  <span className={styles.nodeIndex}>NODE 0{step.id}</span>
                  <div className={styles.nodeOrbit}>
                    <span className={styles.orbitPhoton} />
                    <div className={styles.nodeCore}><Icon /></div>
                  </div>
                  <h3>{step.title.replace(/^\d+\.\s*/, "")}</h3>
                  <p>{step.description}</p>
                  <small><i /> VERIFIED PATH</small>
                </article>
                {index < fanJourney.length - 1 ? (
                  <div className={styles.chainLink} aria-hidden="true">
                    <span className={styles.dataPulse} />
                    <i className={styles.blockOne} />
                    <i className={styles.blockTwo} />
                    <i className={styles.blockThree} />
                  </div>
                ) : null}
              </div>
            );
          })}
        </div>

        <div className={styles.networkFooter}>
          <span><i /> WALLET SELF-CUSTODY</span>
          <p>你始终使用自己的钱包管理链上账户。登录签名不消耗 Gas，也不会授权 Fanora 转移资产；Fanora 不读取或保存私钥与助记词。</p>
          <span><i /> MONAD TESTNET</span>
        </div>
      </div>
    </section>
  );
}
