PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;
CREATE TABLE "CATEGORY" (
	cid INTEGER NOT NULL, 
	parent_id INTEGER, 
	name VARCHAR(100) NOT NULL, 
	description VARCHAR(2000), 
	PRIMARY KEY (cid), 
	FOREIGN KEY(parent_id) REFERENCES "CATEGORY" (cid)
);
INSERT INTO "CATEGORY" VALUES(1,NULL,'featured','featured apps');
CREATE TABLE "USER" (
	uid INTEGER NOT NULL, 
	email VARCHAR(200) NOT NULL, 
	password VARCHAR(200) NOT NULL, 
	fullname VARCHAR(200) NOT NULL, 
	age INTEGER, 
	secondary_email VARCHAR(200),
	summary VARCHAR(200),
	twitter VARCHAR(200),
	author_identifier VARCHAR(100), 
	status INTEGER NOT NULL, 
	role INTEGER NOT NULL, 
	private_key VARCHAR NOT NULL, 
	PRIMARY KEY (uid), 
	UNIQUE (email)
);
INSERT INTO "USER" VALUES(2,'abc@abc.com','pbkdf2:sha1:1000$Ae2WKoPH$1ee27eb85126014800259bbb2f3b906926c7dfba','abc',23,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(3,'test@test.com','pbkdf2:sha1:1000$D7nRVVnb$6e1dc1066570b06a91e8042314bfe1b32613cffb','testing_update 1.0.272',1,'imods.test',0,0,'asdasdasdasd');
INSERT INTO "USER" VALUES(4,'test@swift.com','pbkdf2:sha1:1000$tSbRCjar$9f3dc47be71f775d6aff7bbc8a6c229ee4c1c4af','testing',10,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(5,'test1.101@imods.com','pbkdf2:sha1:1000$2CtVIW92$ed00aecd8ab7bc1644b655646197967e98e4e8f2','testing1.101',10,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(6,'test1.102@imods.com','pbkdf2:sha1:1000$meRRpjjs$5e51f6c0676814858348b5c14a5060bada838ad3','testing1.102',10,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(7,'test1.104@imods.com','pbkdf2:sha1:1000$WryWZFOy$e443bfcba8efdedca8c60860e59c17ed71f65979','testing1.104',10,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(8,'test1.105@imods.com','pbkdf2:sha1:1000$LPlw12GL$909e66b0a8505e1e3ca5b299e475f05c1baa17fb','testing1.105',10,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(9,'test1.106@imods.com','pbkdf2:sha1:1000$0q7jKgj4$16f1cc7cfd0a39d223c814e353a6c53e45268abd','testing1.106',10,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(10,'test1.108@imods.com','pbkdf2:sha1:1000$tdDJlg0Z$ac8fad31c6a8fa08cade7493ffc86d659fcf009b','testing1.108',10,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(11,'test1.110@imods.com','pbkdf2:sha1:1000$wmJy2a9z$baf9327c6cc8cc359d4a9014404b2ec4c13867a1','testing1.110',10,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(12,'test1.111@imods.com','pbkdf2:sha1:1000$dqgdPajU$6f1d80f5499fe37cfa5dc0ea978544a5dcb20069','testing1.111',10,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(13,'test1.114@imods.com','pbkdf2:sha1:1000$mqc8W0DN$914975602bd8aace6205af284f9a80dbf5655f92','testing1.114',10,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(14,'test1.115@imods.com','pbkdf2:sha1:1000$NzwZEW1f$06f1b83c5cd3816b699679e14bb1822026c61e8e','testing1.115',10,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(15,'test1.116@imods.com','pbkdf2:sha1:1000$e9QI7DY7$9deaa5c852f68d9b8d5e1a9e90e0bdb2f00e483d','testing1.116',10,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(16,'test1.117@imods.com','pbkdf2:sha1:1000$vtqdTAtf$761e95e54905f1be7ea195df1e87fa6aae86d046','testing1.117',10,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(17,'test1.118@imods.com','pbkdf2:sha1:1000$SkYFtKX8$1f0fde44ccb389bc342ac9a6471ced981c1daa25','testing1.118',10,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(18,'test1.119@imods.com','pbkdf2:sha1:1000$95QBis0q$4ec8acbf1fbe31adcaf68f76e746e393d4c837b6','testing1.119',10,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(19,'test1.120@imods.com','pbkdf2:sha1:1000$naaLovTk$ab2dfb8b1e75abb71bf231c8b42b96cc54418580','testing1.120',10,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(20,'test1.121@imods.com','pbkdf2:sha1:1000$z5qOEFrJ$8cea3771bc3028254f68cae047a1e557375a94f8','testing1.121',10,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(21,'test1.123@imods.com','pbkdf2:sha1:1000$TxK172iR$0f025c6a825dcb418b7c946573778ba398fcd53e','testing1.123',10,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(22,'test1.124@imods.com','pbkdf2:sha1:1000$5mSSpA2V$f069d4fedcb4adfb792eaab660f8c9ec9fcdd379','testing1.124',10,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(23,'test1.126@imods.com','pbkdf2:sha1:1000$HOCjwqxK$8378c9be7584d19003c06fc0acf9fc2bf3fe492d','testing1.126',10,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(24,'test1.129@imods.com','pbkdf2:sha1:1000$m737Ug0v$e7e0063e7a77534829a753eac883c04162bacff8','testing1.129',10,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(25,'test1.130@imods.com','pbkdf2:sha1:1000$iZyRBXf6$c9c5777170c706d4b204e513ec93f93b5585b7ac','testing1.130',10,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(26,'test1.0.166@imods.com','pbkdf2:sha1:1000$CK0IyRUN$af05a9b31b773f47c12ba1325f886302e17e68f1','testing1.0.166',10,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(27,'test1.0.167@imods.com','pbkdf2:sha1:1000$dkXaKQuO$b1e599751dba4bd0ef81227598c531db391506b5','testing1.0.167',10,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(28,'test1.0.168@imods.com','pbkdf2:sha1:1000$TtSnCOMq$eea007ccc5957c8ce9ac537bda76d10c44b486b3','testing1.0.168',10,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(29,'test1.0.171@imods.com','pbkdf2:sha1:1000$CpbZdU18$07a3e8989ad997d6a1e07aff1553db1974c1128f','testing1.0.171',10,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(30,'test1.0.173@imods.com','pbkdf2:sha1:1000$O1p6CvR2$348474519d8019c7ee68c13c79cd939415f8dcab','testing1.0.173',10,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(31,'test1.0.174@imods.com','pbkdf2:sha1:1000$ge7P3p53$d32ad312b8714867d259034a73680dceeb52a20a','testing1.0.174',10,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(32,'test1.0.175@imods.com','pbkdf2:sha1:1000$FMLXswho$03113489a43aee566689d63ba5bdd784b561658b','testing1.0.175',10,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(33,'test1.0.182@imods.com','pbkdf2:sha1:1000$ql4ugYO5$6702af71aa9fb168d9b020f72c91e5b411216bdb','testing1.0.182',10,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(34,'test1.0.194@imods.com','pbkdf2:sha1:1000$b4KqwAIy$9d9b09a9f8710e5b3a61ebf8d8d20008b7e50a38','testing1.0.194',10,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(35,'test1.0.195@imods.com','pbkdf2:sha1:1000$PZWgY9q4$9aec1184e533b5022a494edca0c052d2887bca36','testing1.0.195',10,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(36,'test1.0.196@imods.com','pbkdf2:sha1:1000$z0hTVaYG$b434070da0b4aaa62f9caa1dc612cb6ffa20059f','testing1.0.196',10,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(37,'test1.0.197@imods.com','pbkdf2:sha1:1000$BROzuLyx$7818207981c246a4cc0870495778f23ca72bd035','testing1.0.197',10,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(38,'test1.0.198@imods.com','pbkdf2:sha1:1000$aSrgTgNe$a16f6e066ece45db251b7036f2e4c06f45367c53','testing1.0.198',10,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(39,'test1.0.199@imods.com','pbkdf2:sha1:1000$v5grskkn$a0a0a3028cc16291a920a46103cfe3c43f391bb5','testing1.0.199',10,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(40,'test1.0.200@imods.com','pbkdf2:sha1:1000$yRF3C7I1$22a0d33d8054b8e4dbab836478386140238d4d70','testing1.0.200',10,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(41,'test1.0.201@imods.com','pbkdf2:sha1:1000$MJlntTDC$2fa1df3f51bd3524e9ed4c5e95ea7e903e66ba05','testing1.0.201',10,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(42,'test1.0.202@imods.com','pbkdf2:sha1:1000$oURHGcHa$22fc907a123096cae63b8fe751dbfec4bc44ea94','testing1.0.202',10,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(43,'test1.0.203@imods.com','pbkdf2:sha1:1000$6QBKLTKM$1266ff2ead0c246450b5cde809023eaaf725abae','testing1.0.203',10,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(44,'test1.0.204@imods.com','pbkdf2:sha1:1000$bDuHlsfJ$6f55c15bdf89625633373dcf1c6e8a305c2ad2df','testing1.0.204',10,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(45,'test1.0.205@imods.com','pbkdf2:sha1:1000$yVjpCQaN$dec78663954663de115a210a8f03d2be71316230','testing1.0.205',10,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(46,'test1.0.206@imods.com','pbkdf2:sha1:1000$UUQ9u6KQ$8294c439afe9411b13d6f2354770488285958b1b','testing1.0.206',10,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(47,'test1.0.208@imods.com','pbkdf2:sha1:1000$vmYG3KGi$7e1ba83616dcf8a921a81d73734a04e83e776235','testing1.0.208',10,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(48,'test1.0.209@imods.com','pbkdf2:sha1:1000$dFMefJfc$64245653fc424518179bcf442f15d4b3896abcef','testing1.0.209',10,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(49,'test1.0.215@imods.com','pbkdf2:sha1:1000$R7ABH0KK$1bbb85fd2eb6e2dc39ef9fd6562514e4e23e7537','testing1.0.215',10,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(50,'test1.0.216@imods.com','pbkdf2:sha1:1000$ajjoNC6c$ecafc99a05a306a759ee13602801b19931170b83','testing1.0.216',10,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(51,'test1.0.217@imods.com','pbkdf2:sha1:1000$T55xMhc9$df9eb7ba9837f929f4d6ec78de8476f5c30618ef','testing1.0.217',10,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(52,'test1.0.218@imods.com','pbkdf2:sha1:1000$tM8O9LGU$e66246dc525cf9602ccb35dc807c9665f6943ce4','testing1.0.218',10,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(53,'test1.0.219@imods.com','pbkdf2:sha1:1000$IiRYhIlK$8772756c4c4e325299c05ef4552f282c6ca72535','testing1.0.219',10,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(54,'test1.0.220@imods.com','pbkdf2:sha1:1000$2pzwQ6tQ$b367331300ceb728e9b1f0e482b7762813616415','testing1.0.220',10,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(55,'test1.0.221@imods.com','pbkdf2:sha1:1000$kP0kMJJS$778e027ffa3ca2300f6303ad6b9c3d6ed9eaea12','testing1.0.221',10,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(56,'test1.0.222@imods.com','pbkdf2:sha1:1000$jZeUEcpc$5746acd4255fc14445b672d45bb99d23013eb580','testing1.0.222',10,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(57,'test1.0.224@imods.com','pbkdf2:sha1:1000$BYAuSQFw$252a9908cfbc201b1c7d3664349ca57b503dfee0','testing1.0.224',10,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(58,'test1.0.225@imods.com','pbkdf2:sha1:1000$8eTrNNd1$3a059f67177058f7e3ee731ff635be228481a7c4','testing1.0.225',10,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(59,'test1.0.226@imods.com','pbkdf2:sha1:1000$kPZbeSmR$2a68694970089b1ef0d3c92e67d310473665a928','testing1.0.226',10,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(60,'test1.0.227@imods.com','pbkdf2:sha1:1000$s6Xse0YA$1b7072b6f37a45b78347af072d19e8fcd8db5cc2','testing1.0.227',10,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(61,'test1.0.228@imods.com','pbkdf2:sha1:1000$35tWznLe$dd066b318e8f44fca68708a7b6e337d6d4bf5b66','testing1.0.228',10,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(62,'test1.0.229@imods.com','pbkdf2:sha1:1000$HpdxUb4b$33e6ed7ea17218f75a04bb99c55197a1fe7623ea','testing1.0.229',10,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(63,'test1.0.230@imods.com','pbkdf2:sha1:1000$8YsSKa2r$8a85adeb30199ff8a3e10959c53690ad4d1e4aa9','testing1.0.230',10,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(64,'test1.0.231@imods.com','pbkdf2:sha1:1000$GjDFTYyS$3e95b4e909ce7ccb0d3bdb2f242af443cfb3f67c','testing1.0.231',10,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(65,'test1.0.232@imods.com','pbkdf2:sha1:1000$xW2As66j$254b36b73d644ccf9ac1b985c60819117d254614','testing1.0.232',10,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(66,'test1.0.233@imods.com','pbkdf2:sha1:1000$naVTywv2$285b205fb492c78935bf9e822583a0aebbb7042c','testing1.0.233',10,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(67,'test1.0.234@imods.com','pbkdf2:sha1:1000$ZkbrZzS4$6443ff65e5c0e5d2a6873543116d24f053a05888','testing1.0.234',10,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(68,'test1.0.235@imods.com','pbkdf2:sha1:1000$4tXFvNua$fc09c40e02bc463679b57df16020d8713ecd7f3a','testing1.0.235',10,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(69,'test1.0.256@imods.com','pbkdf2:sha1:1000$PkOQP6tu$37d6db171557e655ea6b84b0a1877af2767b5176','testing1.0.256',10,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(70,'test1.0.257@imods.com','pbkdf2:sha1:1000$LOUKqUq6$91a4a834e506ec59d966f8a40aff95c880593626','testing1.0.257',10,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(71,'test1.0.258@imods.com','pbkdf2:sha1:1000$8FiPWPtC$15f499032caea6f168f31eb976c9b158a6df2dc9','testing1.0.258',10,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(72,'test1.0.259@imods.com','pbkdf2:sha1:1000$DGkpXQd5$577c8b2b403a83930e8199a647bbd4be427fc8ee','testing1.0.259',10,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(73,'test1.0.262@imods.com','pbkdf2:sha1:1000$cWhxIymI$e31ee27ebad06bcf71f3c9ee579c1b65130bb539','testing1.0.262',10,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(74,'test1.0.264@imods.com','pbkdf2:sha1:1000$sqPxlGO6$b093eff985b8f961dc5af2cf4c6eba98ff77d69a','testing1.0.264',10,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(75,'test1.0.266@imods.com','pbkdf2:sha1:1000$seeDPsaU$12a3f875634b99ded1e62b89c24149f163ee0fde','testing1.0.266',10,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(76,'test1.0.267@imods.com','pbkdf2:sha1:1000$fn9dzr4B$f46b9f9b9422d79e200ec256601e3e406c723a35','testing1.0.267',10,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(77,'test1.0.268@imods.com','pbkdf2:sha1:1000$NRbuU9Fr$3b0bde35ba64663eef898071a141d3b26686acac','testing1.0.268',10,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(78,'test1.0.269@imods.com','pbkdf2:sha1:1000$mffhvJsP$0a23832a7f5b7c9f0cfb38e8877fb828e5e46f86','testing1.0.269',10,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(79,'test1.0.270@imods.com','pbkdf2:sha1:1000$6yH1R34h$28f7645e7b32e67b64a3ab1094a169a40e42a5d9','testing1.0.270',10,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(80,'testing-1.0.271','pbkdf2:sha1:1000$bLfIpHaH$88355aad218bbacfc9b0719cb37ce15f2cd9e063','test-1.0.271@imods.com',10,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(81,'testing-1.0.272','pbkdf2:sha1:1000$6AGJILbe$85b6da11faf4726ac3151022b562983f077d18ef','test-1.0.272@imods.com',10,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(82,'testing-1.0.275','pbkdf2:sha1:1000$84gpoIgS$073a86614f78e48a2b0962aab988acce4830c12c','testing_update 1.0.275',11,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(83,'testing-1.0.276','pbkdf2:sha1:1000$aZkBS9he$af7294e278ea5454344cd36add808c8db2db2417','testing_update 1.0.276',11,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(84,'testing-1.0.277','pbkdf2:sha1:1000$uvdnodOp$7c0f8c63a81f2a6b9ab0d3c7a91affd4e6bd5ab6','testing_update 1.0.277',1,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(85,'testing-1.0.280','pbkdf2:sha1:1000$Oe44OZFI$920ee25bea2d7c9bf60ebdfb7a78dd16e4cff667','testing_update 1.0.280',11,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(86,'testing-1.0.281','pbkdf2:sha1:1000$vPIbrOwZ$143374c20ae765cc49337a203d27587400e26938','testing_update 1.0.281',11,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(87,'testing-1.0.283','pbkdf2:sha1:1000$AyHwuiEn$480b35acabccb4646713a290ef213c480c557f04','test-1.0.283@imods.com',10,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(88,'testing-1.0.284','pbkdf2:sha1:1000$OCweoErX$8fa1b3235d52c25e2dd7e23df3b59dcd1eab10bf','test-1.0.284@imods.com',10,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(89,'testing-1.0.365','pbkdf2:sha1:1000$wF0vuxrY$4217411a45161283c2a60ad66f8b14ce57caf3c0','test-1.0.365@imods.com',10,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(90,'testing-1.0.366','pbkdf2:sha1:1000$laepyMZ0$941a95242452961e4a9cae372263ce3e44865c20','test-1.0.366@imods.com',10,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(91,'testing-1.0.367','pbkdf2:sha1:1000$9wOzWL6p$b9a41dd944250751008e70e5a324cbf130fc8618','testing_update 1.0.367',11,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(92,'testing-1.0.370','pbkdf2:sha1:1000$2qGypGmZ$e89e4054f9ce0639b21ae5e9e0b1069911152782','testing_update 1.0.370',11,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(93,'testing-1.0.393','pbkdf2:sha1:1000$P6tfNw4r$91e44468f5560df7c6717ea235b03d520a7bc565','testing_update 1.0.393',1,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(94,'testing-1.0.394','pbkdf2:sha1:1000$JK8puu7I$37dbdc55cde5ef6754a68d3130af715aa27e2771','testing_update 1.0.394',11,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(95,'testing-1.0.416','pbkdf2:sha1:1000$ThqLTB1F$fca28d8693a98a36612fe539d535e52fedaf40af','testing_update 1.0.416',11,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(96,'testing-1.0.418','pbkdf2:sha1:1000$CDKLjlSN$8b20226ce107a88d80dbb172f6687d7402230fe5','testing_update 1.0.418',11,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(97,'testing-1.0.422','pbkdf2:sha1:1000$fay2WEgV$cf6e28f28ff1da228ec59613210a2153e45c35aa','testing_update 1.0.422',11,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(98,'testing-1.0.425','pbkdf2:sha1:1000$Juh2MRdl$7a775f39401139af7a52aba2fb98a6e8abca709c','testing_update 1.0.425',11,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(99,'testing-1.0.426','pbkdf2:sha1:1000$HqjJXZev$de1467642abcc888e92c621a7d72748306427c33','testing_update 1.0.426',11,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(100,'testing-1.0.427','pbkdf2:sha1:1000$KTJLit2i$4cb38d1b5ba01f618df8c079e9b72d676c858cb7','testing_update 1.0.427',11,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(101,'testing-1.0.428','pbkdf2:sha1:1000$zxaXZ71v$7676887dfc5dc93340d2a5f5c0ec029fbd850470','testing_update 1.0.428',11,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(102,'testing-1.0.456','pbkdf2:sha1:1000$5dranyjl$f4776a1a5f9beeab2ea1e861e7c31af1e7085dd1','testing_update 1.0.456',11,'author_identifier',0,100,'privatekey');
INSERT INTO "USER" VALUES(103,'testing-1.0.505','pbkdf2:sha1:1000$Ufwl9jf0$c34d6f8306356a5f804ba045e2d27b4fcd3b6001','test-1.0.505@imods.com',10,'author_identifier',0,100,'privatekey');
CREATE TABLE "ITEM" (
	iid INTEGER NOT NULL, 
	category_id INTEGER, 
	author_id VARCHAR(100), 
	pkg_name VARCHAR(200) NOT NULL, 
	display_name VARCHAR(100) NOT NULL, 
	pkg_version VARCHAR(100) NOT NULL, 
	pkg_signature VARCHAR, 
	pkg_path VARCHAR, 
	pkg_assets_path VARCHAR, 
	pkg_dependencies VARCHAR, 
	pkg_conflicts VARCHAR,
	pkg_predepends VARCHAR,
	price FLOAT, 
	summary VARCHAR(500), 
	description VARCHAR,
	changelog VARCHAR,
	status INTEGER DEFAULT 1,
	type VARCHAR,
	downloads INTEGER DEFAULT 0,
	control VARCHAR,
	add_date DATE NOT NULL, 
	last_update_date DATE NOT NULL, 
	PRIMARY KEY (iid), 
	FOREIGN KEY(category_id) REFERENCES "CATEGORY" (cid) ON DELETE CASCADE, 
	FOREIGN KEY(author_id) REFERENCES "USER" (author_identifier), 
	UNIQUE (pkg_name)
);
CREATE TABLE "BILLING_INFO" (
	bid INTEGER NOT NULL, 
	uid INTEGER, 
	address VARCHAR(200) NOT NULL, 
	zipcode INTEGER NOT NULL, 
	city VARCHAR(100) NOT NULL, 
	state VARCHAR(100) NOT NULL, 
	country VARCHAR(100) NOT NULL, 
	type_ VARCHAR(200) NOT NULL, 
	cc_no VARCHAR(100), 
	cc_expr DATE, 
	cc_name VARCHAR(200), 
	PRIMARY KEY (bid), 
	FOREIGN KEY(uid) REFERENCES "USER" (uid)
);
CREATE TABLE "DEVICE" (
	dev_id INTEGER NOT NULL, 
	uid INTEGER, 
	device_name VARCHAR(200) NOT NULL, 
	"IMEI" VARCHAR(100) NOT NULL, 
	"UDID" VARCHAR(200) NOT NULL, 
	model VARCHAR(100) NOT NULL, 
	PRIMARY KEY (dev_id), 
	FOREIGN KEY(uid) REFERENCES "USER" (uid) ON DELETE CASCADE
);
CREATE TABLE "REVIEW" (
	rid INTEGER NOT NULL, 
	uid INTEGER, 
	iid INTEGER, 
	rating INTEGER NOT NULL, 
	title VARCHAR(50) NOT NULL,
	content VARCHAR(500) NOT NULL, 
	add_date DATETIME NOT NULL,
	PRIMARY KEY (rid), 
	FOREIGN KEY(uid) REFERENCES "USER" (uid), 
	FOREIGN KEY(iid) REFERENCES "ITEM" (iid)
);
CREATE TABLE "WISHLIST" (
	uid INTEGER, 
	iid INTEGER, 
	FOREIGN KEY(uid) REFERENCES "USER" (uid), 
	FOREIGN KEY(iid) REFERENCES "ITEM" (iid)
);
INSERT INTO "WISHLIST" VALUES(5,2);
CREATE TABLE "ORDER" (
	oid INTEGER NOT NULL, 
	uid INTEGER, 
	pkg_name VARCHAR(200), 
	billing_id INTEGER, 
	quantity INTEGER NOT NULL, 
	currency VARCHAR(3) NOT NULL, 
	total_price FLOAT, 
	status INTEGER NOT NULL, 
	total_charged FLOAT, 
	order_date DATETIME NOT NULL, 
	PRIMARY KEY (oid), 
	FOREIGN KEY(uid) REFERENCES "USER" (uid) ON DELETE CASCADE, 
	FOREIGN KEY(pkg_name) REFERENCES "ITEM" (pkg_name), 
	FOREIGN KEY(billing_id) REFERENCES "BILLING_INFO" (bid)
);
CREATE TABLE "SIGNUPCODES" (
    code VARCHAR NOT NULL,
    PRIMARY KEY(code)
);
CREATE TABLE "VIPUSERS" (
    vip_email VARCHAR NOT NULL,
    PRIMARY KEY(vip_email)
;)
COMMIT;
